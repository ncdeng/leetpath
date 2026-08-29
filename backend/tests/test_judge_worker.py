import os
import subprocess
import sys
import time

import pytest

from judge import worker


def test_process_output_is_capped_and_terminated():
    result = worker._run_process_limited(
        [sys.executable, "-c", "import sys; sys.stdout.write('x' * 100000)"],
        timeout=10,
        output_limit=1024,
    )
    assert result.returncode == worker.OUTPUT_LIMIT_RETURN_CODE
    assert len(result.stdout.encode("utf-8")) <= 1024


def test_runtime_container_uses_security_boundaries(tmp_path, monkeypatch):
    captured: list[str] = []

    def fake_run(args, timeout, *, container_name=None):
        captured.extend(args)
        return subprocess.CompletedProcess(args, 0, "ok\n", "")

    monkeypatch.setattr(worker, "_run_docker", fake_run)
    monkeypatch.setattr(worker, "_force_rm_container", lambda _name: None)
    job = worker.JobData(
        submission_id=1,
        language="python3",
        code="print('ok')",
        time_limit_ms=1000,
        memory_limit_mb=128,
        cases=(),
        io_mode="acm",
        problem_slug="two-sum",
        leetcode_spec=None,
    )
    case = worker.CaseData(ordinal=1, input_text="", expected_output="ok", is_sample=True)
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "001.in").write_text("", encoding="utf-8")

    status, _, _, _ = worker._run_case(job, tmp_path, case, "python-image", "python3 main.py")

    assert status == worker.STATUS_AC
    assert ["--user", "65534:65534"] == captured[captured.index("--user"):captured.index("--user") + 2]
    assert ["--cap-drop", "ALL"] == captured[captured.index("--cap-drop"):captured.index("--cap-drop") + 2]
    assert ["--security-opt", "no-new-privileges"] == captured[
        captured.index("--security-opt"):captured.index("--security-opt") + 2
    ]


def test_compile_container_has_matching_security_limits(tmp_path, monkeypatch):
    captured: list[str] = []

    def fake_run(args, timeout, *, container_name=None):
        captured.extend(args)
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(worker, "_run_docker", fake_run)
    assert worker._compile_cpp(tmp_path) is None
    for expected in (
        "--read-only",
        "--pids-limit",
        "--cap-drop",
        "--security-opt",
        "--user",
        "--tmpfs",
    ):
        assert expected in captured


def test_compile_mounts_only_source_not_tests_dir(tmp_path, monkeypatch):
    """编译阶段整目录挂载会让 #include "tests/003.in" 把隐藏用例回显进编译报错"""
    captured: list[str] = []

    def fake_run(args, timeout, *, container_name=None):
        captured.extend(args)
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(worker, "_run_docker", fake_run)
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "003.in").write_text("secret-case", encoding="utf-8")

    assert worker._compile_cpp(tmp_path) is None

    volumes = [captured[i + 1] for i, arg in enumerate(captured) if arg == "-v"]
    assert any(v.endswith(":/work/main.cpp:ro") for v in volumes)
    # work_dir 整体（含 tests/）不得进入编译容器
    assert not any(v.endswith(":/work") or v.endswith(":/work:ro") for v in volumes)
    assert not any("tests" in v for v in volumes)


def test_prepare_workdir_wraps_leetcode_solution(tmp_path, monkeypatch):
    from judge.leetcode_catalog import spec_for

    monkeypatch.setattr(worker.tempfile, "gettempdir", lambda: str(tmp_path))
    job = worker.JobData(
        submission_id=42,
        language="python3",
        code="class Solution:\n    def twoSum(self, nums, target):\n        return [0, 1]\n",
        time_limit_ms=1000,
        memory_limit_mb=128,
        cases=(worker.CaseData(ordinal=1, input_text="2\n1 2\n3\n", expected_output="0 1\n", is_sample=True),),
        io_mode="leetcode",
        problem_slug="two-sum",
        leetcode_spec=spec_for("two-sum"),
    )
    root = worker._prepare_workdir(job)
    source = (root / "main.py").read_text(encoding="utf-8")
    assert "class Solution:" in source
    assert "def twoSum" in source
    assert "json.loads" in source
    assert "if __name__" in source


def test_output_limit_closes_streams_without_waiting_on_blocked_writer():
    import time

    started = time.monotonic()
    result = worker._run_process_limited(
        [
            sys.executable,
            "-c",
            "import sys, time\n"
            "sys.stdout.write('x' * 8_000_000)\n"
            "sys.stdout.flush()\n"
            "time.sleep(30)\n",
        ],
        timeout=10,
        output_limit=2048,
    )
    elapsed = time.monotonic() - started
    assert result.returncode == worker.OUTPUT_LIMIT_RETURN_CODE
    assert len(result.stdout.encode("utf-8")) <= 2048
    assert elapsed < 5


def test_infra_error_compile_output_is_sanitized(admin_client, tmp_path, monkeypatch):
    from app import db as dbmod
    from app.models import Problem, Submission, Testcase

    leaked = str(tmp_path / "secret" / "host-worker.py")
    created = admin_client.post(
        "/api/submissions",
        json={"problem_slug": "two-sum", "language": "python3", "code": "print(1)"},
    ).json()
    assert dbmod.SessionLocal is not None
    with dbmod.SessionLocal() as db:
        submission = db.get(Submission, created["id"])
        assert submission is not None
        submission.status = "judging"
        db.commit()

    def explode(_job):
        raise RuntimeError(
            f"Traceback (most recent call last):\n  File \"{leaked}\", line 1\nboom"
        )

    monkeypatch.setattr(worker, "evaluate", explode)
    worker.process_submission(dbmod.SessionLocal, Submission, Problem, Testcase, created["id"])

    with dbmod.SessionLocal() as db:
        submission = db.get(Submission, created["id"])
        assert submission is not None
        assert submission.status == "IE"
        output = submission.compile_output or ""
        assert output == worker.USER_IE_MESSAGE
        assert "Traceback" not in output
        assert leaked not in output
        assert str(tmp_path) not in output


def test_write_result_requires_judging_status(admin_client):
    from app import db as dbmod
    from app.models import Submission

    created = admin_client.post(
        "/api/submissions",
        json={"problem_slug": "two-sum", "language": "python3", "code": "print(1)"},
    ).json()
    sub_id = created["id"]
    assert dbmod.SessionLocal is not None

    with dbmod.SessionLocal() as db:
        assert worker._write_result(
            db, Submission, sub_id, worker.STATUS_AC, 12, [{"ordinal": 1, "status": "AC"}], None
        ) is False
        assert db.get(Submission, sub_id).status == "pending"

        db.get(Submission, sub_id).status = "judging"
        db.commit()

    with dbmod.SessionLocal() as db:
        assert worker._write_result(
            db,
            Submission,
            sub_id,
            worker.STATUS_WA,
            8,
            [{"ordinal": 1, "status": "WA"}],
            None,
        ) is True
        row = db.get(Submission, sub_id)
        assert row.status == "WA"
        assert row.runtime_ms == 8
        assert row.detail[0]["status"] == "WA"


def test_worker_recovers_orphaned_judging_submissions(admin_client):
    from app import db as dbmod
    from app.models import Submission

    created = admin_client.post(
        "/api/submissions",
        json={"problem_slug": "two-sum", "language": "python3", "code": "print(1)"},
    ).json()
    assert dbmod.SessionLocal is not None
    with dbmod.SessionLocal() as db:
        submission = db.get(Submission, created["id"])
        assert submission is not None
        submission.status = "judging"
        db.commit()

    with dbmod.SessionLocal() as db:
        assert worker.recover_orphaned_judging(db, Submission) == 1

    with dbmod.SessionLocal() as db:
        assert db.get(Submission, created["id"]).status == "pending"


def _make_job(**overrides) -> worker.JobData:
    fields = {
        "submission_id": 1,
        "language": "python3",
        "code": "print('ok')",
        "time_limit_ms": 1000,
        "memory_limit_mb": 128,
        "cases": (),
        "io_mode": "acm",
        "problem_slug": "two-sum",
        "leetcode_spec": None,
    }
    fields.update(overrides)
    return worker.JobData(**fields)


def _make_case(ordinal: int = 1) -> worker.CaseData:
    return worker.CaseData(ordinal=ordinal, input_text="", expected_output="ok", is_sample=True)


def _make_tests_dir(tmp_path, ordinal: int = 1):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / f"{ordinal:03d}.in").write_text("", encoding="utf-8")
    return tests_dir


def test_run_case_mounts_only_current_case_not_whole_dir(tmp_path, monkeypatch):
    captured: list[str] = []

    def fake_run(args, timeout, *, container_name=None):
        captured.extend(args)
        return subprocess.CompletedProcess(args, 0, "ok\n", "")

    monkeypatch.setattr(worker, "_run_docker", fake_run)
    monkeypatch.setattr(worker, "_force_rm_container", lambda _name: None)
    _make_tests_dir(tmp_path, ordinal=2)

    status, _, _, _ = worker._run_case(
        _make_job(), tmp_path, _make_case(ordinal=2), "python-image", "python3 main.py"
    )

    assert status == worker.STATUS_AC
    volumes = [captured[i + 1] for i, arg in enumerate(captured) if arg == "-v"]
    # 只挂当前用例与源码文件；整目录挂载会让用户代码读到全部隐藏用例
    assert any(v.endswith(":/tests/current.in:ro") and "002.in" in v for v in volumes)
    assert any(v.endswith(":/work/main.py:ro") for v in volumes)
    assert not any(v.endswith(":/work:ro") for v in volumes)


def test_run_case_maps_outer_timeout_to_ie(tmp_path, monkeypatch):
    def fake_run(args, timeout, *, container_name=None):
        return subprocess.CompletedProcess(args, -1, "", "")

    monkeypatch.setattr(worker, "_run_docker", fake_run)
    monkeypatch.setattr(worker, "_force_rm_container", lambda _name: None)
    _make_tests_dir(tmp_path)

    status, _, _, stderr = worker._run_case(
        _make_job(), tmp_path, _make_case(), "python-image", "python3 main.py"
    )

    # docker CLI 被外层超时强杀是基础设施问题，不该冤枉用户 TLE
    assert status == worker.STATUS_IE
    assert stderr == worker.USER_IE_MESSAGE


def test_user_exit_code_3_is_re_not_ce(tmp_path, monkeypatch):
    """用户程序 sys.exit(3) 必须判 RE：预检查已移出运行容器，退出码不再共用命名空间"""
    def fake_run(args, timeout, *, container_name=None):
        return subprocess.CompletedProcess(args, 3, "", "")

    monkeypatch.setattr(worker, "_run_docker", fake_run)
    monkeypatch.setattr(worker, "_force_rm_container", lambda _name: None)
    _make_tests_dir(tmp_path)

    status, _, _, _ = worker._run_case(
        _make_job(), tmp_path, _make_case(), "python-image", "python3 main.py"
    )

    assert status == worker.STATUS_RE


def test_run_case_container_command_has_no_precheck(tmp_path, monkeypatch):
    """运行容器内只有一条 timeout 命令，不含 || / ; 复合结构"""
    captured: list[str] = []

    def fake_run(args, timeout, *, container_name=None):
        captured.extend(args)
        return subprocess.CompletedProcess(args, 0, "ok\n", "")

    monkeypatch.setattr(worker, "_run_docker", fake_run)
    monkeypatch.setattr(worker, "_force_rm_container", lambda _name: None)
    _make_tests_dir(tmp_path)

    worker._run_case(_make_job(), tmp_path, _make_case(), "python-image", "python3 main.py")

    inner = captured[-1]
    assert inner.startswith("timeout -s KILL")
    assert "py_compile" not in inner
    assert "||" not in inner
    assert ";" not in inner


def test_python_syntax_error_maps_to_ce_via_precheck(tmp_path, monkeypatch):
    """语法错误在独立预检查阶段判 CE，且不进入任何用例容器"""
    monkeypatch.setattr(worker.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(worker, "_precheck_python", lambda _wd: "SyntaxError: invalid syntax")
    monkeypatch.setattr(
        worker, "_run_case", lambda *a, **k: pytest.fail("CE 后不应再跑任何用例")
    )
    job = _make_job(
        cases=(worker.CaseData(ordinal=1, input_text="", expected_output="", is_sample=True),)
    )

    status, runtime_ms, detail, compile_output = worker.evaluate(job)

    assert status == worker.STATUS_CE
    assert runtime_ms is None
    assert detail == []
    assert "SyntaxError" in (compile_output or "")


def test_precheck_python_runs_once_per_submission(tmp_path, monkeypatch):
    """预检查是独立阶段：多用例提交也只跑一次，不随用例数重复"""
    monkeypatch.setattr(worker.tempfile, "gettempdir", lambda: str(tmp_path))
    calls: list[str] = []

    def fake_precheck(work_dir):
        calls.append(str(work_dir))
        return None

    monkeypatch.setattr(worker, "_precheck_python", fake_precheck)
    monkeypatch.setattr(
        worker, "_run_case", lambda *a, **k: (worker.STATUS_AC, 5, "", "")
    )
    job = _make_job(
        cases=tuple(
            worker.CaseData(ordinal=i, input_text="", expected_output="", is_sample=False)
            for i in range(1, 4)
        )
    )

    status, _, detail, _ = worker.evaluate(job)

    assert status == worker.STATUS_AC
    assert len(detail) == 3
    assert len(calls) == 1


def test_precheck_python_mounts_only_source_file(tmp_path, monkeypatch):
    """预检查容器同样只挂 main.py，不得暴露 tests/"""
    captured: list[str] = []

    def fake_run(args, timeout, *, container_name=None):
        captured.extend(args)
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(worker, "_run_docker", fake_run)
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "001.in").write_text("secret", encoding="utf-8")

    assert worker._precheck_python(tmp_path) is None

    volumes = [captured[i + 1] for i, arg in enumerate(captured) if arg == "-v"]
    assert any(v.endswith(":/work/main.py:ro") for v in volumes)
    assert not any("tests" in v for v in volumes)
    assert "py_compile" in captured


def test_cleanup_stale_artifacts_removes_exited_containers_and_old_dirs(tmp_path, monkeypatch):
    removed: list[str] = []
    monkeypatch.setattr(
        worker,
        "_run_docker",
        lambda args, timeout: subprocess.CompletedProcess(args, 0, "cid1\ncid2\n", ""),
    )
    monkeypatch.setattr(worker, "_force_rm_container", lambda name: removed.append(name))
    monkeypatch.setattr(worker.tempfile, "gettempdir", lambda: str(tmp_path))
    old_dir = tmp_path / "lpj-11"
    old_dir.mkdir()
    stale = time.time() - 7200
    os.utime(old_dir, (stale, stale))
    fresh_dir = tmp_path / "lpj-12"
    fresh_dir.mkdir()

    containers, dirs = worker.cleanup_stale_artifacts()

    assert containers == 2
    assert removed == ["cid1", "cid2"]
    assert dirs == 1
    assert not old_dir.exists()
    assert fresh_dir.exists()
