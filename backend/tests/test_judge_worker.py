import subprocess
import sys

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
    container_names: list[str] = []
    removed_names: list[str] = []

    def fake_run(args, timeout, *, container_name=None):
        captured.extend(args)
        container_names.append(container_name)
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(worker, "_run_docker", fake_run)
    monkeypatch.setattr(worker, "_force_rm_container", removed_names.append)
    assert worker._compile_cpp(tmp_path) is None
    assert "--rm" not in captured
    assert removed_names == container_names
    for expected in (
        "--read-only",
        "--pids-limit",
        "--cap-drop",
        "--security-opt",
        "--user",
        "--tmpfs",
    ):
        assert expected in captured


def _runtime_job() -> worker.JobData:
    return worker.JobData(
        submission_id=7,
        language="python3",
        code="",
        time_limit_ms=1000,
        memory_limit_mb=128,
        cases=(),
        io_mode="acm",
        problem_slug="two-sum",
        leetcode_spec=None,
    )


@pytest.mark.parametrize(
    ("returncode", "message"),
    (
        (1, "docker: user-controlled message"),
        (1, "cannot connect is just program output"),
        (125, "no such image is also program output"),
    ),
)
def test_runtime_docker_keywords_from_exited_user_program_are_re(
    tmp_path,
    monkeypatch,
    returncode,
    message,
):
    def fake_run(args, timeout, *, container_name=None):
        return subprocess.CompletedProcess(args, returncode, "", message)

    monkeypatch.setattr(worker, "_run_docker", fake_run)
    monkeypatch.setattr(
        worker,
        "_inspect_container_exit_state",
        lambda _name: worker.ContainerExitState(returncode, False),
    )
    monkeypatch.setattr(worker, "_force_rm_container", lambda _name: None)

    status, _, _, stderr = worker._run_case(
        _runtime_job(),
        tmp_path,
        worker.CaseData(ordinal=1, input_text="", expected_output="", is_sample=False),
        "python-image",
        "python3 main.py",
    )

    assert status == worker.STATUS_RE
    assert stderr == message


@pytest.mark.parametrize(
    "message",
    (
        "docker: compiler diagnostic",
        "cannot connect appears in source diagnostic",
        "no such image appears in source diagnostic",
    ),
)
def test_compile_docker_keywords_from_exited_compiler_are_ce(tmp_path, monkeypatch, message):
    def fake_run(args, timeout, *, container_name=None):
        return subprocess.CompletedProcess(args, 1, "", message)

    monkeypatch.setattr(worker, "_run_docker", fake_run)
    monkeypatch.setattr(
        worker,
        "_inspect_container_exit_state",
        lambda _name: worker.ContainerExitState(1, False),
    )
    monkeypatch.setattr(worker, "_force_rm_container", lambda _name: None)

    assert worker._compile_cpp(tmp_path) == message


def test_runtime_docker_run_failure_without_exited_container_is_ie(tmp_path, monkeypatch):
    def fake_run(args, timeout, *, container_name=None):
        return subprocess.CompletedProcess(args, 125, "", "docker: daemon unavailable")

    monkeypatch.setattr(worker, "_run_docker", fake_run)
    monkeypatch.setattr(worker, "_inspect_container_exit_state", lambda _name: None)
    monkeypatch.setattr(worker, "_force_rm_container", lambda _name: None)

    with pytest.raises(worker.JudgeInfraError, match="daemon unavailable"):
        worker._run_case(
            _runtime_job(),
            tmp_path,
            worker.CaseData(ordinal=1, input_text="", expected_output="", is_sample=False),
            "python-image",
            "python3 main.py",
        )


def test_compile_docker_run_failure_without_exited_container_is_ie(tmp_path, monkeypatch):
    def fake_run(args, timeout, *, container_name=None):
        return subprocess.CompletedProcess(args, 125, "", "docker: daemon unavailable")

    monkeypatch.setattr(worker, "_run_docker", fake_run)
    monkeypatch.setattr(worker, "_inspect_container_exit_state", lambda _name: None)
    monkeypatch.setattr(worker, "_force_rm_container", lambda _name: None)

    with pytest.raises(worker.JudgeInfraError, match="daemon unavailable"):
        worker._compile_cpp(tmp_path)


@pytest.mark.parametrize(
    ("state_json", "expected"),
    (
        (
            '{"Status":"exited","ExitCode":137,"OOMKilled":true}',
            worker.ContainerExitState(137, True),
        ),
        ('{"Status":"created","ExitCode":125,"OOMKilled":false}', None),
        ("not-json", None),
    ),
)
def test_inspect_container_exit_state_requires_exited_state(monkeypatch, state_json, expected):
    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess([], 0, state_json, "")

    monkeypatch.setattr(worker.subprocess, "run", fake_run)

    assert worker._inspect_container_exit_state("lpj-test") == expected


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
