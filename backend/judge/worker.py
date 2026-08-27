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
import traceback
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

STATUS_AC = "AC"
STATUS_WA = "WA"
STATUS_TLE = "TLE"
STATUS_MLE = "MLE"
STATUS_CE = "CE"
STATUS_RE = "RE"
STATUS_IE = "IE"
STATUS_JUDGING = "judging"
STATUS_PENDING = "pending"


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


@dataclass(frozen=True)
class ContainerExitState:
    exit_code: int
    oom_killed: bool


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


def _inspect_container_exit_state(name: str) -> ContainerExitState | None:
    """返回已实际运行并退出的容器状态；不存在、未启动或 inspect 失败时返回 None。"""
    try:
        r = subprocess.run(
            [DOCKER_BIN, "inspect", "-f", "{{json .State}}", name],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except Exception:
        return None
    if r.returncode != 0:
        return None
    try:
        state = json.loads(r.stdout)
        if not isinstance(state, dict) or state.get("Status") != "exited":
            return None
        exit_code = state.get("ExitCode")
        if isinstance(exit_code, bool):
            return None
        return ContainerExitState(
            exit_code=int(exit_code),
            oom_killed=state.get("OOMKilled") is True,
        )
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def _require_container_exit_state(
    name: str,
    result: subprocess.CompletedProcess[str],
) -> ContainerExitState:
    """确认非零 docker run 来自已退出容器，而不是 Docker 基础设施失败。"""
    state = _inspect_container_exit_state(name)
    if state is None or state.exit_code == 0:
        raise JudgeInfraError(
            _truncate(
                (result.stderr or result.stdout or "docker run 失败").strip(),
                COMPILE_OUTPUT_LIMIT,
            )
        )
    return state


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
        while True:
            chunk = stream.read(65536)
            if not chunk:
                return
            with lock:
                used = len(buffers["stdout"]) + len(buffers["stderr"])
                remaining = max(0, output_limit - used)
                buffers[name].extend(chunk[:remaining])
                if len(chunk) > remaining:
                    output_exceeded.set()
                    return

    threads = [
        threading.Thread(target=read_stream, args=("stdout", process.stdout), daemon=True),
        threading.Thread(target=read_stream, args=("stderr", process.stderr), daemon=True),
    ]
    for thread in threads:
        thread.start()

    deadline = time.monotonic() + timeout
    timed_out = False
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
    """单 worker 启动时回收上一次进程遗留的 judging 提交。"""
    from sqlalchemy import update

    result = session.execute(
        update(Submission)
        .where(Submission.status == STATUS_JUDGING)
        .values(status=STATUS_PENDING)
    )
    session.commit()
    return int(result.rowcount or 0)


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
    return root


def _compile_cpp(work_dir: Path) -> str | None:
    """成功返回 None；失败返回截断后的编译器输出。"""
    args = [
        "run",
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
    name = _container_name("ce", work_dir.name)
    try:
        r = _run_docker(
            args,
            timeout=COMPILE_TIMEOUT_S,
            container_name=name,
        )
        if r.returncode == -1:
            return _truncate("编译超时", COMPILE_OUTPUT_LIMIT)
        if r.returncode == OUTPUT_LIMIT_RETURN_CODE:
            return "编译输出超过 1 MiB 限制"
        if r.returncode != 0:
            _require_container_exit_state(name, r)
            msg = r.stderr if r.stderr.strip() else r.stdout
            return _truncate(msg, COMPILE_OUTPUT_LIMIT)
        return None
    finally:
        _force_rm_container(name)


def _run_case(
    job: JobData,
    work_dir: Path,
    case: CaseData,
    image: str,
    inner_cmd: str,
) -> tuple[str, int, str, str]:
    """返回 (status, runtime_ms, stdout, stderr)。runtime_ms 为外层 wall time（含容器启动开销）。"""
    limit_s = max(1, math.ceil(job.time_limit_ms / 1000))
    infile = f"tests/{case.ordinal:03d}.in"
    inner = f"timeout -s KILL {limit_s} {inner_cmd} < {infile}"
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
        "-v", _docker_volume(work_dir, "/work", read_only=True),
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

        if r.returncode == -1:
            return STATUS_TLE, runtime_ms, stdout, stderr
        if r.returncode == OUTPUT_LIMIT_RETURN_CODE:
            return STATUS_RE, runtime_ms, stdout, "程序输出超过 1 MiB 限制"
        if r.returncode == 0:
            if normalize(stdout) == normalize(case.expected_output):
                return STATUS_AC, runtime_ms, stdout, stderr
            return STATUS_WA, runtime_ms, stdout, stderr

        state = _require_container_exit_state(name, r)
        if state.exit_code == 124:
            return STATUS_TLE, runtime_ms, stdout, stderr
        if state.exit_code == 137:
            # GNU timeout -s KILL 经 docker 常为 137 且 OOMKilled=false；cgroup OOM 为 137 且 OOMKilled=true。
            if state.oom_killed:
                return STATUS_MLE, runtime_ms, stdout, stderr
            return STATUS_TLE, runtime_ms, stdout, stderr
        return STATUS_RE, runtime_ms, stdout, stderr
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
        else:
            image = JUDGE_IMAGE_CPP
            inner_cmd = "./main_bin"

        details: list[dict[str, Any]] = []
        overall = STATUS_AC
        max_runtime = 0
        for case in job.cases:
            status, runtime_ms, stdout, stderr = _run_case(job, work_dir, case, image, inner_cmd)
            details.append(_case_detail(case, status, runtime_ms, stdout, stderr))
            max_runtime = max(max_runtime, runtime_ms)
            if status != STATUS_AC:
                overall = status
                break
        return overall, max_runtime, details, None
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def _assign_detail(submission: Any, detail: list[dict[str, Any]] | None) -> None:
    if detail is None:
        submission.detail = None
        return
    try:
        col = submission.__table__.c.detail
        type_name = type(col.type).__name__.lower()
        if "json" in type_name:
            submission.detail = detail
        else:
            submission.detail = json.dumps(detail, ensure_ascii=False)
    except Exception:
        submission.detail = detail


def _write_result(
    session: Any,
    Submission: Any,
    submission_id: int,
    status: str,
    runtime_ms: int | None,
    detail: list[dict[str, Any]] | None,
    compile_output: str | None,
) -> None:
    submission = session.get(Submission, submission_id)
    if submission is None:
        log.error("写回失败：submission id=%s 不存在", submission_id)
        return
    submission.status = status
    submission.runtime_ms = runtime_ms
    if hasattr(submission, "judged_at"):
        submission.judged_at = datetime.now(timezone.utc).replace(tzinfo=None)
    _assign_detail(submission, detail)
    submission.compile_output = compile_output
    session.commit()


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
    except Exception as e:
        log.exception("评测异常 submission id=%s", submission_id)
        msg = traceback.format_exc() if not isinstance(e, JudgeInfraError) else str(e)
        try:
            with SessionLocal() as session:
                _write_result(
                    session,
                    Submission,
                    submission_id,
                    STATUS_IE,
                    None,
                    None,
                    _truncate(msg, COMPILE_OUTPUT_LIMIT),
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
                continue
            log.info("领取 submission id=%s", sub_id)
            process_submission(SessionLocal, Submission, Problem, Testcase, sub_id)
        except KeyboardInterrupt:
            log.info("收到中断，退出")
            raise
        except Exception:
            log.exception("轮询循环异常，继续")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
