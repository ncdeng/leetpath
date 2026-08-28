"""判题 worker：轮询 pending 提交，用一次性 Docker 容器评测并写回结果。

在 backend/ 目录运行：python -m judge.worker
"""

from __future__ import annotations

import json
import logging
import math
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

log = logging.getLogger("judge.worker")

POLL_INTERVAL = float(os.environ.get("POLL_INTERVAL", "1.0"))
JUDGE_IMAGE_PYTHON = os.environ.get("JUDGE_IMAGE_PYTHON", "leetpath-judge-python")
JUDGE_IMAGE_CPP = os.environ.get("JUDGE_IMAGE_CPP", "leetpath-judge-cpp")
DOCKER_BIN = os.environ.get("DOCKER_BIN", "docker")

COMPILE_OUTPUT_LIMIT = 4000
STDERR_LIMIT = 500
WA_OUTPUT_LIMIT = 500
SAMPLE_IO_LIMIT = 1000
COMPILE_TIMEOUT_S = 60
OUTPUT_LIMIT_BYTES = 1024 * 1024
OUTPUT_LIMIT_RETURN_CODE = -2
# 评测容器内预检查（py_compile）失败时约定的退出码，区别于运行期错误的 1
CE_PRECHECK_RETURN_CODE = 3

STATUS_AC = "AC"
STATUS_WA = "WA"
STATUS_TLE = "TLE"
STATUS_MLE = "MLE"
STATUS_CE = "CE"
STATUS_RE = "RE"
STATUS_IE = "IE"
STATUS_JUDGING = "judging"
STATUS_PENDING = "pending"

# 写给用户的 IE 文案：不含宿主机路径、Traceback 或 Docker 细节。
USER_IE_MESSAGE = "评测系统异常，请稍后重试"


class JudgeInfraError(Exception):
    """Docker / 镜像等基础设施异常，对应提交状态 IE。"""


@dataclass(frozen=True)
class CaseData:
    ordinal: int
    input_text: str
    expected_output: str
    is_sample: bool


@dataclass(frozen=True)
class JobData:
    submission_id: int
    language: str
    code: str
    time_limit_ms: int
    memory_limit_mb: int
    cases: tuple[CaseData, ...]
    io_mode: str
    problem_slug: str
    leetcode_spec: dict | None


def normalize(s: str) -> str:
    """每行去行尾空白，整体去掉末尾空行（与 seed 校验器一致）。"""
    lines = [ln.rstrip() for ln in s.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def _truncate(s: str, n: int) -> str:
    if len(s) <= n:
        return s
    return s[:n]


def public_ie_output(_internal: object | None = None) -> str:
    """IE 时给用户的 compile_output。内部异常只进日志。"""
    return USER_IE_MESSAGE


def _close_stream(stream: Any) -> None:
    if stream is None:
        return
    try:
        stream.close()
    except Exception:
        pass


def _docker_volume(host: Path, dest: str, read_only: bool = False) -> str:
    """构造 docker -v 参数。Windows 保留原生盘符路径，避免 D:/x:/work:ro 被拆错。"""
    path = str(host.resolve())
    suffix = ":ro" if read_only else ""
    return f"{path}:{dest}{suffix}"


def _container_name(*parts: object) -> str:
    token = uuid.uuid4().hex[:8]
    raw = "-".join(str(p) for p in parts if p is not None)
    return f"lpj-{raw}-{token}"


def _force_rm_container(name: str) -> None:
    try:
        subprocess.run(
            [DOCKER_BIN, "rm", "-f", name],
            capture_output=True,
            timeout=20,
        )
    except Exception:
        pass


def _container_oom_killed(name: str) -> bool:
    """评测容器不带 --rm，以便在退出码 137 时读取 OOMKilled，区分 TLE 与 MLE。"""
    try:
        r = subprocess.run(
            [DOCKER_BIN, "inspect", "-f", "{{.State.OOMKilled}}", name],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except Exception:
        return False
    return r.returncode == 0 and r.stdout.strip().lower() == "true"


def _run_docker(
    args: list[str],
    timeout: float,
    *,
    container_name: str | None = None,
) -> subprocess.CompletedProcess[str]:
    if container_name and args and args[0] == "run":
        args = ["run", "--name", container_name, *args[1:]]
    cmd = [DOCKER_BIN, *args]
    try:
        result = _run_process_limited(cmd, timeout=timeout, output_limit=OUTPUT_LIMIT_BYTES)
        if result.returncode in (-1, OUTPUT_LIMIT_RETURN_CODE) and container_name:
            _force_rm_container(container_name)
        return result
    except FileNotFoundError as e:
        raise JudgeInfraError(f"找不到 docker 可执行文件 ({DOCKER_BIN}): {e}") from e


def _run_process_limited(
    cmd: list[str],
    *,
    timeout: float,
    output_limit: int,
) -> subprocess.CompletedProcess[str]:
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    lock = threading.Lock()
    output_exceeded = threading.Event()

    def read_stream(name: str, stream: Any) -> None:
        try:
            while True:
                if output_exceeded.is_set():
                    return
                chunk = stream.read(65536)
                if not chunk:
                    return
                with lock:
                    used = len(buffers["stdout"]) + len(buffers["stderr"])
                    remaining = max(0, output_limit - used)
                    if remaining == 0:
                        output_exceeded.set()
                        return
                    buffers[name].extend(chunk[:remaining])
                    if len(chunk) > remaining:
                        output_exceeded.set()
                        return
        except (ValueError, OSError):
            return
        finally:
            _close_stream(stream)

    threads = [
        threading.Thread(target=read_stream, args=("stdout", process.stdout), daemon=True),
        threading.Thread(target=read_stream, args=("stderr", process.stderr), daemon=True),
    ]
    for thread in threads:
        thread.start()

    deadline = time.monotonic() + timeout
    timed_out = False
    try:
        while process.poll() is None:
            if output_exceeded.is_set():
                process.kill()
                break
            if time.monotonic() >= deadline:
                timed_out = True
                process.kill()
                break
            time.sleep(0.01)
        process.wait()
        for thread in threads:
            thread.join(timeout=1)
    finally:
        _close_stream(process.stdout)
        _close_stream(process.stderr)

    if output_exceeded.is_set():
        returncode = OUTPUT_LIMIT_RETURN_CODE
    elif timed_out:
        returncode = -1
    else:
        returncode = process.returncode
    return subprocess.CompletedProcess(
        cmd,
        returncode,
        buffers["stdout"].decode("utf-8", "replace"),
        buffers["stderr"].decode("utf-8", "replace"),
    )


def _image_inspect(image: str) -> subprocess.CompletedProcess[str]:
    return _run_docker(["image", "inspect", image], timeout=30)


def require_images() -> None:
    """启动时检查两镜像存在；缺失则退出并提示构建命令。"""
    missing: list[str] = []
    for image in (JUDGE_IMAGE_PYTHON, JUDGE_IMAGE_CPP):
        try:
            r = _image_inspect(image)
        except JudgeInfraError as e:
            raise SystemExit(str(e)) from e
        if r.returncode != 0:
            err = (r.stderr or r.stdout or "").strip()
            lowered = err.lower()
            if "cannot connect" in lowered or "daemon" in lowered or "npipe" in lowered:
                raise SystemExit(f"Docker 不可用: {err}")
            missing.append(image)
    if missing:
        names = ", ".join(missing)
        raise SystemExit(
            f"缺少判题镜像: {names}\n"
            "请在 backend/ 目录执行:\n"
            "  docker build -t leetpath-judge-python -f judge/Dockerfile.python judge\n"
            "  docker build -t leetpath-judge-cpp    -f judge/Dockerfile.cpp judge"
        )


def _import_app():
    try:
        from app import db as app_db  # type: ignore
        from app.models import Problem, Submission, Testcase  # type: ignore
    except ImportError as e:
        raise SystemExit(
            "无法导入 app.db / app.models。"
            "请在 backend/ 目录运行 python -m judge.worker，并确保 app 包可用。"
            f" 原始错误: {e}"
        ) from e
    # app.db 在 configure_db() 之前 SessionLocal 为 None（FastAPI lifespan 里才会初始化）。
    if getattr(app_db, "SessionLocal", None) is None:
        configure = getattr(app_db, "configure_db", None)
        if configure is not None:
            configure()
        elif getattr(app_db, "engine", None) is not None:
            from sqlalchemy.orm import sessionmaker

            app_db.SessionLocal = sessionmaker(bind=app_db.engine, expire_on_commit=False)
        else:
            raise SystemExit("app.db 未导出 SessionLocal / configure_db / engine")
    session_factory = getattr(app_db, "SessionLocal", None)
    if session_factory is None:
        raise SystemExit("app.db 初始化后仍无 SessionLocal")
    return session_factory, Problem, Submission, Testcase


def _load_job(session: Any, submission: Any, Problem: Any, Testcase: Any) -> JobData:
    from sqlalchemy import select

    problem = session.get(Problem, submission.problem_id)
    if problem is None:
        raise JudgeInfraError(f"提交 {submission.id} 引用的题目 {submission.problem_id} 不存在")
    rows = session.scalars(
        select(Testcase)
        .where(Testcase.problem_id == submission.problem_id)
        .order_by(Testcase.ordinal.asc())
    ).all()
    cases = tuple(
        CaseData(
            ordinal=int(row.ordinal),
            input_text="" if row.input is None else str(row.input),
            expected_output="" if row.expected_output is None else str(row.expected_output),
            is_sample=bool(row.is_sample),
        )
        for row in rows
    )
    time_limit_ms = int(getattr(problem, "time_limit_ms", None) or 5000)
    memory_limit_mb = int(getattr(problem, "memory_limit_mb", None) or 256)
    if time_limit_ms <= 0:
        time_limit_ms = 5000
    if memory_limit_mb <= 0:
        memory_limit_mb = 256
    spec = getattr(problem, "leetcode_spec", None)
    if not isinstance(spec, dict):
        try:
            from judge.leetcode_catalog import spec_for_problem

            spec = spec_for_problem(problem)
        except Exception:
            spec = None
    return JobData(
        submission_id=int(submission.id),
        language=str(submission.language or ""),
        code="" if submission.code is None else str(submission.code),
        time_limit_ms=time_limit_ms,
        memory_limit_mb=memory_limit_mb,
        cases=cases,
        io_mode=str(getattr(submission, "io_mode", None) or "acm"),
        problem_slug=str(getattr(problem, "slug", "") or ""),
        leetcode_spec=spec if isinstance(spec, dict) else None,
    )


def claim_pending(session: Any, Submission: Any) -> int | None:
    """按 id 升序领取最早 pending；UPDATE ... status='pending' 且 rowcount=1 才算成功。

    返回 submission id，调用方随后在独立会话中加载数据，避免评测期间长时间占用连接。
    """
    from sqlalchemy import select, update

    sub_id = session.scalar(
        select(Submission.id)
        .where(Submission.status == STATUS_PENDING)
        .order_by(Submission.id.asc())
        .limit(1)
    )
    if sub_id is None:
        return None
    result = session.execute(
        update(Submission)
        .where(Submission.id == sub_id, Submission.status == STATUS_PENDING)
        .values(status=STATUS_JUDGING)
    )
    session.commit()
    if result.rowcount != 1:
        return None
    return int(sub_id)


def recover_orphaned_judging(session: Any, Submission: Any) -> int:
    """把 judging 提交打回 pending。

    单 worker 串行评测：一轮结束时仍处于 judging 的提交必然是强杀/外力
    遗留的孤儿。启动时调用清历史遗留，主循环每轮结尾调用当看门狗，
    避免卡死的 judging 占住在途配额（MAX_GLOBAL_IN_FLIGHT 按 pending+judging 计数）。
    """
    from sqlalchemy import update

    result = session.execute(
        update(Submission)
        .where(Submission.status == STATUS_JUDGING)
        .values(status=STATUS_PENDING)
    )
    session.commit()
    return int(result.rowcount or 0)


def cleanup_stale_artifacts() -> tuple[int, int]:
    """清理上次异常退出遗留的已停评测容器与过期临时目录，避免随时间累积。

    只动「已退出」的 lpj-* 容器和超过 1 小时未变更的 workdir，
    不会碰仍在运行的其他 worker 的活跃资源。
    """
    removed_containers = 0
    try:
        r = _run_docker(
            ["ps", "-aq", "--filter", "name=lpj-", "--filter", "status=exited"],
            timeout=30,
        )
        if r.returncode == 0:
            for cid in r.stdout.split():
                _force_rm_container(cid.strip())
                removed_containers += 1
    except JudgeInfraError:
        pass
    removed_dirs = 0
    cutoff = time.time() - 3600
    for entry in Path(tempfile.gettempdir()).glob("lpj-*"):
        try:
            if entry.is_dir() and entry.stat().st_mtime < cutoff:
                shutil.rmtree(entry, ignore_errors=True)
                removed_dirs += 1
        except OSError:
            continue
    return removed_containers, removed_dirs


def _start_heartbeat() -> threading.Thread:
    """后台线程周期性 touch 心跳文件，供 compose healthcheck 探测 worker 是否存活。

    评测在主线程串行执行，单次评测可能长达数分钟，心跳放在独立线程
    才不会在长评测期间被误判为卡死。
    """
    path = Path(tempfile.gettempdir()) / "lpj-worker-heartbeat"

    def beat() -> None:
        while True:
            try:
                path.touch()
            except OSError:
                pass
            time.sleep(10)

    thread = threading.Thread(target=beat, daemon=True)
    thread.start()
    return thread


def _prepare_workdir(job: JobData) -> Path:
    root = Path(tempfile.gettempdir()) / f"lpj-{job.submission_id}"
    if root.exists():
        shutil.rmtree(root, ignore_errors=False)
    tests_dir = root / "tests"
    tests_dir.mkdir(parents=True)
    filename = "main.py" if job.language == "python3" else "main.cpp"
    source = job.code.replace("\r\n", "\n")
    if job.io_mode == "leetcode":
        from judge.leetcode_wrap import wrap_user_code

        source = wrap_user_code(job.language, source, job.leetcode_spec)
    (root / filename).write_text(source, encoding="utf-8", newline="\n")
    for case in job.cases:
        (tests_dir / f"{case.ordinal:03d}.in").write_text(
            case.input_text.replace("\r\n", "\n"),
            encoding="utf-8",
            newline="\n",
        )
    root.chmod(0o777)
    # 隐藏用例只应经 docker 单文件挂载进容器；宿主侧收紧到属主可读，
    # 避免同机其他用户直接翻看隐藏用例
    tests_dir.chmod(0o700)
    return root


def _compile_cpp(work_dir: Path) -> str | None:
    """成功返回 None；失败返回截断后的编译器输出。"""
    args = [
        "run",
        "--rm",
        "--network", "none",
        "--read-only",
        "--tmpfs", "/tmp:size=32m",
        "--memory", "512m",
        "--memory-swap", "512m",
        "--cpus", "1",
        "--pids-limit", "64",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--user", "65534:65534",
        "-v", _docker_volume(work_dir, "/work"),
        "-w", "/work",
        JUDGE_IMAGE_CPP,
        "g++", "-O2", "-std=c++17", "-o", "main_bin", "main.cpp",
    ]
    r = _run_docker(
        args,
        timeout=COMPILE_TIMEOUT_S,
        container_name=_container_name("ce", work_dir.name),
    )
    if r.returncode == -1:
        return _truncate("编译超时", COMPILE_OUTPUT_LIMIT)
    if r.returncode == OUTPUT_LIMIT_RETURN_CODE:
        return "编译输出超过 1 MiB 限制"
    if r.returncode != 0 and (r.returncode == 125 or _looks_like_docker_failure(r)):
        raise JudgeInfraError(
            _truncate((r.stderr or r.stdout or "docker run 失败").strip(), COMPILE_OUTPUT_LIMIT)
        )
    if r.returncode != 0:
        msg = r.stderr if r.stderr.strip() else r.stdout
        return _truncate(msg, COMPILE_OUTPUT_LIMIT)
    return None


def _looks_like_docker_failure(r: subprocess.CompletedProcess[str]) -> bool:
    """只匹配 stderr 首行，避免用户程序自己打印含 docker 字样的输出被误判为基础设施故障。"""
    lines = (r.stderr or "").strip().splitlines()
    first = lines[0].lower() if lines else ""
    needles = (
        "unable to find image",
        "cannot connect",
        "error response from daemon",
        "unknown flag",
        "docker: ",
        "is not running",
        "no such image",
    )
    return any(n in first for n in needles)


def _run_case(
    job: JobData,
    work_dir: Path,
    case: CaseData,
    image: str,
    inner_cmd: str,
    pre_cmd: str | None = None,
) -> tuple[str, int, str, str]:
    """返回 (status, runtime_ms, stdout, stderr)。runtime_ms 为外层 wall time（含容器启动开销）。

    只把当前用例的 .in 与源码文件单独挂进容器：整目录挂载会让用户代码
    直接读到全部隐藏用例输入。
    """
    limit_s = max(1, math.ceil(job.time_limit_ms / 1000))
    code_file = "main.py" if job.language == "python3" else "main_bin"
    infile_host = work_dir / "tests" / f"{case.ordinal:03d}.in"
    timed = f"timeout -s KILL {limit_s} {inner_cmd} < /tests/current.in"
    if pre_cmd:
        # 预检查失败走独立退出码，与运行期错误区分（如 python 语法错误应判 CE）
        inner = f"{pre_cmd} || exit {CE_PRECHECK_RETURN_CODE}; {timed}"
    else:
        inner = timed
    mem = f"{job.memory_limit_mb}m"
    # 不用 --rm：timeout -s KILL 在容器内也返回 137，必须 inspect OOMKilled 才能和 MLE 区分；结束后显式 rm。
    args = [
        "run",
        "--network", "none",
        "--read-only",
        "--tmpfs", "/tmp:size=32m",
        "--memory", mem,
        "--memory-swap", mem,  # 关闭 swap，否则超内存往往变成 TLE
        "--cpus", "0.5",
        "--pids-limit", "64",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--user", "65534:65534",
        "-v", _docker_volume(work_dir / code_file, f"/work/{code_file}", read_only=True),
        "-v", _docker_volume(infile_host, "/tests/current.in", read_only=True),
        "-w", "/work",
        image,
        "sh", "-c", inner,
    ]
    outer_timeout = limit_s + 15
    name = _container_name(job.submission_id, case.ordinal)
    t0 = time.perf_counter()
    try:
        r = _run_docker(args, timeout=outer_timeout, container_name=name)
        runtime_ms = max(0, int((time.perf_counter() - t0) * 1000))
        stdout = r.stdout or ""
        stderr = r.stderr or ""
        oom = _container_oom_killed(name) if r.returncode != -1 else False

        if r.returncode == -1:
            # docker CLI 被外层超时强杀：几乎必然是容器启动慢/宿主拥塞，
            # 内层 timeout 才是真正的程序超时，这里判 IE 而不是冤枉用户 TLE
            return STATUS_IE, runtime_ms, stdout, USER_IE_MESSAGE
        if r.returncode == OUTPUT_LIMIT_RETURN_CODE:
            return STATUS_RE, runtime_ms, stdout, "程序输出超过 1 MiB 限制"
        if r.returncode == CE_PRECHECK_RETURN_CODE:
            return STATUS_CE, runtime_ms, stdout, stderr
        if r.returncode == 124:
            return STATUS_TLE, runtime_ms, stdout, stderr
        if r.returncode == 137:
            # GNU timeout -s KILL 经 docker 常为 137 且 OOMKilled=false；cgroup OOM 为 137 且 OOMKilled=true。
            if oom:
                return STATUS_MLE, runtime_ms, stdout, stderr
            return STATUS_TLE, runtime_ms, stdout, stderr
        if r.returncode != 0:
            if r.returncode == 125 or _looks_like_docker_failure(r):
                raise JudgeInfraError(
                    _truncate((stderr or stdout or "docker run 失败").strip(), COMPILE_OUTPUT_LIMIT)
                )
            return STATUS_RE, runtime_ms, stdout, stderr
        if normalize(stdout) == normalize(case.expected_output):
            return STATUS_AC, runtime_ms, stdout, stderr
        return STATUS_WA, runtime_ms, stdout, stderr
    finally:
        _force_rm_container(name)


def _case_detail(
    case: CaseData,
    status: str,
    runtime_ms: int,
    stdout: str,
    stderr: str,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "ordinal": case.ordinal,
        "is_sample": case.is_sample,
        "status": status,
        "runtime_ms": runtime_ms,
    }
    if case.is_sample:
        item["input"] = _truncate(case.input_text, SAMPLE_IO_LIMIT)
        item["expected"] = _truncate(case.expected_output, SAMPLE_IO_LIMIT)
        out_limit = WA_OUTPUT_LIMIT if status == STATUS_WA else SAMPLE_IO_LIMIT
        item["output"] = _truncate(stdout, out_limit)
    if status == STATUS_RE:
        item["stderr"] = _truncate(stderr, STDERR_LIMIT)
    return item


def evaluate(job: JobData) -> tuple[str, int | None, list[dict[str, Any]], str | None]:
    """评测一份提交。返回 (status, runtime_ms, detail, compile_output)。"""
    if job.language not in ("python3", "cpp"):
        raise JudgeInfraError(f"不支持的语言: {job.language}")
    if not job.cases:
        raise JudgeInfraError(f"题目没有测试用例 (submission {job.submission_id})")

    try:
        work_dir = _prepare_workdir(job)
    except ValueError as exc:
        return STATUS_CE, None, [], str(exc)
    try:
        if job.language == "cpp":
            compile_output = _compile_cpp(work_dir)
            if compile_output is not None:
                return STATUS_CE, None, [], compile_output

        if job.language == "python3":
            image = JUDGE_IMAGE_PYTHON
            inner_cmd = "python3 main.py"
            # python 没有编译阶段：语法错误会被判成 RE + 一屏 traceback。
            # 先 py_compile 预检查，失败判 CE；pycache 指到 /tmp（/work 只读）。
            pre_cmd = "PYTHONPYCACHEPREFIX=/tmp/pyc python3 -m py_compile main.py"
        else:
            image = JUDGE_IMAGE_CPP
            inner_cmd = "./main_bin"
            pre_cmd = None

        details: list[dict[str, Any]] = []
        overall = STATUS_AC
        max_runtime = 0
        compile_output: str | None = None
        for case in job.cases:
            status, runtime_ms, stdout, stderr = _run_case(
                job, work_dir, case, image, inner_cmd, pre_cmd
            )
            details.append(_case_detail(case, status, runtime_ms, stdout, stderr))
            max_runtime = max(max_runtime, runtime_ms)
            if status != STATUS_AC:
                overall = status
                if status == STATUS_CE:
                    compile_output = _truncate(stderr, COMPILE_OUTPUT_LIMIT)
                break
        return overall, max_runtime, details, compile_output
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def _serialize_detail(Submission: Any, detail: list[dict[str, Any]] | None) -> Any:
    if detail is None:
        return None
    try:
        col = Submission.__table__.c.detail
        type_name = type(col.type).__name__.lower()
        if "json" in type_name:
            return detail
        return json.dumps(detail, ensure_ascii=False)
    except Exception:
        return detail


def _write_result(
    session: Any,
    Submission: Any,
    submission_id: int,
    status: str,
    runtime_ms: int | None,
    detail: list[dict[str, Any]] | None,
    compile_output: str | None,
) -> bool:
    """仅当提交仍处于 judging 时写回，避免覆盖已回收或已终态的记录。"""
    from sqlalchemy import update

    values: dict[str, Any] = {
        "status": status,
        "runtime_ms": runtime_ms,
        "compile_output": compile_output,
        "detail": _serialize_detail(Submission, detail),
    }
    if hasattr(Submission, "judged_at"):
        values["judged_at"] = datetime.now(timezone.utc).replace(tzinfo=None)

    result = session.execute(
        update(Submission)
        .where(Submission.id == submission_id, Submission.status == STATUS_JUDGING)
        .values(**values)
    )
    session.commit()
    if result.rowcount != 1:
        log.warning(
            "跳过写回：submission id=%s 不是 judging（rowcount=%s）",
            submission_id,
            result.rowcount,
        )
        return False
    return True


def process_submission(
    SessionLocal: Any,
    Submission: Any,
    Problem: Any,
    Testcase: Any,
    submission_id: int,
) -> None:
    work_dir = Path(tempfile.gettempdir()) / f"lpj-{submission_id}"
    try:
        with SessionLocal() as session:
            submission = session.get(Submission, submission_id)
            if submission is None:
                log.error("领取后找不到 submission id=%s", submission_id)
                return
            job = _load_job(session, submission, Problem, Testcase)
        status, runtime_ms, detail, compile_output = evaluate(job)
        with SessionLocal() as session:
            _write_result(
                session, Submission, submission_id, status, runtime_ms, detail, compile_output
            )
        log.info(
            "完成 submission id=%s status=%s runtime_ms=%s cases=%s",
            submission_id,
            status,
            runtime_ms,
            len(detail),
        )
    except Exception:
        log.exception("评测异常 submission id=%s", submission_id)
        try:
            with SessionLocal() as session:
                _write_result(
                    session,
                    Submission,
                    submission_id,
                    STATUS_IE,
                    None,
                    None,
                    public_ie_output(),
                )
        except Exception:
            log.exception("写回 IE 失败 submission id=%s", submission_id)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    SessionLocal, Problem, Submission, Testcase = _import_app()
    with SessionLocal() as session:
        recovered = recover_orphaned_judging(session, Submission)
    if recovered:
        log.warning("已回收 %s 个遗留 judging 提交", recovered)
    require_images()
    cleaned_containers, cleaned_dirs = cleanup_stale_artifacts()
    if cleaned_containers or cleaned_dirs:
        log.info("清理遗留评测容器 %s 个、临时目录 %s 个", cleaned_containers, cleaned_dirs)
    _start_heartbeat()
    log.info(
        "worker 启动 poll=%.1fs python=%s cpp=%s",
        POLL_INTERVAL,
        JUDGE_IMAGE_PYTHON,
        JUDGE_IMAGE_CPP,
    )
    while True:
        try:
            with SessionLocal() as session:
                sub_id = claim_pending(session, Submission)
            if sub_id is None:
                time.sleep(POLL_INTERVAL)
            else:
                log.info("领取 submission id=%s", sub_id)
                process_submission(SessionLocal, Submission, Problem, Testcase, sub_id)
        except KeyboardInterrupt:
            log.info("收到中断，退出")
            raise
        except Exception:
            log.exception("轮询循环异常，继续")
            time.sleep(POLL_INTERVAL)
        try:
            with SessionLocal() as session:
                if recover_orphaned_judging(session, Submission):
                    log.warning("看门狗回收了遗留 judging 提交")
        except Exception:
            log.exception("看门狗回收异常，继续")


if __name__ == "__main__":
    main()
