from datetime import date, timedelta

import pytest


def test_jobs_crud_admin(admin_client):
    empty = admin_client.get("/api/jobs")
    assert empty.status_code == 200
    assert empty.json() == []

    soon = (date.today() + timedelta(days=3)).isoformat()
    later = (date.today() + timedelta(days=10)).isoformat()
    created = admin_client.post(
        "/api/jobs",
        json={
            "company": "字节跳动",
            "position": "后端开发",
            "batch": "2026秋招",
            "deadline_at": later,
            "jd_text": "熟悉 Python",
            "apply_url": "https://example.com/apply",
        },
    )
    assert created.status_code == 201
    job = created.json()
    assert job["company"] == "字节跳动"
    assert job["status"] == "open"
    assert job["days_left"] == 10
    job_id = job["id"]

    admin_client.post(
        "/api/jobs",
        json={"company": "阿里巴巴", "position": "客户端", "deadline_at": soon},
    )
    listed = admin_client.get("/api/jobs").json()
    assert [j["company"] for j in listed] == ["阿里巴巴", "字节跳动"]
    assert listed[0]["days_left"] == 3

    updated = admin_client.put(f"/api/jobs/{job_id}", json={"status": "closed", "position": "资深后端"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "closed"
    assert updated.json()["position"] == "资深后端"

    deleted = admin_client.delete(f"/api/jobs/{job_id}")
    assert deleted.status_code == 204
    remaining = admin_client.get("/api/jobs").json()
    assert len(remaining) == 1
    assert remaining[0]["company"] == "阿里巴巴"


def test_jobs_null_deadline_last(admin_client):
    admin_client.post("/api/jobs", json={"company": "无截止日期", "position": "P6"})
    d = (date.today() + timedelta(days=1)).isoformat()
    admin_client.post("/api/jobs", json={"company": "有截止日期", "position": "P6", "deadline_at": d})
    names = [j["company"] for j in admin_client.get("/api/jobs").json()]
    assert names == ["有截止日期", "无截止日期"]
    assert admin_client.get("/api/jobs").json()[1]["days_left"] is None


def test_jobs_non_admin_forbidden(user_client):
    r = user_client.post("/api/jobs", json={"company": "X", "position": "Y"})
    assert r.status_code == 403
    listed = user_client.get("/api/jobs")
    assert listed.status_code == 200


def test_job_track_sync(admin_client, user_client):
    # admin_client / user_client 共享同一 TestClient，注册 bob 后会话已切到 bob，
    # 需要用 login 显式切换回管理员 admin 建岗
    r = admin_client.post("/api/auth/login", json={"username": "admin", "password": "password123"})
    assert r.status_code == 200
    job = admin_client.post("/api/jobs", json={"company": "腾讯", "position": "后端"}).json()
    job_id = job["id"]

    r = user_client.post("/api/auth/login", json={"username": "bob", "password": "password123"})
    assert r.status_code == 200
    assert user_client.get("/api/jobs/track").json() == {}

    r = user_client.put(f"/api/jobs/{job_id}/track", json={"status": "applied"})
    assert r.status_code == 200
    assert r.json()["status"] == "applied"
    assert user_client.get("/api/jobs/track").json() == {str(job_id): "applied"}

    r = user_client.put(f"/api/jobs/{job_id}/track", json={"status": "interview"})
    assert r.json()["status"] == "interview"

    # 非法状态与不存在岗位
    assert user_client.put(f"/api/jobs/{job_id}/track", json={"status": "hacked"}).status_code == 422
    assert user_client.put("/api/jobs/99999/track", json={"status": "applied"}).status_code == 404

    # none 清除
    user_client.put(f"/api/jobs/{job_id}/track", json={"status": "none"})
    assert user_client.get("/api/jobs/track").json() == {}

    # 另一个用户的标记互不影响
    admin_client.post("/api/auth/login", json={"username": "admin", "password": "password123"})
    admin_client.put(f"/api/jobs/{job_id}/track", json={"status": "offer"})
    assert admin_client.get("/api/jobs/track").json() == {str(job_id): "offer"}
    user_client.post("/api/auth/login", json={"username": "bob", "password": "password123"})
    assert user_client.get("/api/jobs/track").json() == {}


def test_deleting_job_removes_existing_tracks(admin_client, user_client):
    admin_client.post("/api/auth/login", json={"username": "admin", "password": "password123"})
    job = admin_client.post(
        "/api/jobs", json={"company": "待删除公司", "position": "后端"}
    ).json()
    job_id = job["id"]

    user_client.post("/api/auth/login", json={"username": "bob", "password": "password123"})
    assert user_client.put(
        f"/api/jobs/{job_id}/track", json={"status": "applied"}
    ).status_code == 200

    admin_client.post("/api/auth/login", json={"username": "admin", "password": "password123"})
    assert admin_client.delete(f"/api/jobs/{job_id}").status_code == 204

    from app import db as dbmod
    from app.models import Job, JobTrack

    with dbmod.SessionLocal() as db:
        assert db.get(Job, job_id) is None
        assert db.query(JobTrack).filter(JobTrack.job_id == job_id).count() == 0


def test_job_urls_must_use_https(admin_client):
    base = {"company": "示例公司", "position": "开发", "tier": "small"}
    javascript = admin_client.post("/api/jobs", json={**base, "apply_url": "javascript:alert(1)"})
    assert javascript.status_code == 422
    insecure = admin_client.post("/api/jobs", json={**base, "apply_url": "http://example.com"})
    assert insecure.status_code == 422
    secure = admin_client.post("/api/jobs", json={**base, "apply_url": "https://example.com/apply"})
    assert secure.status_code == 201
    assert secure.json()["apply_url"] == "https://example.com/apply"


@pytest.mark.parametrize("field", ["company", "position", "tier", "status"])
def test_job_update_rejects_null_required_fields(admin_client, field):
    created = admin_client.post(
        "/api/jobs",
        json={"company": "示例公司", "position": "开发", "tier": "small"},
    )
    response = admin_client.put(f"/api/jobs/{created.json()['id']}", json={field: None})
    assert response.status_code == 422


def test_jobs_hide_legacy_non_https_urls(admin_client):
    from app import db as dbmod
    from app.models import Job

    assert dbmod.SessionLocal is not None
    with dbmod.SessionLocal() as db:
        db.add(
            Job(
                company="历史数据",
                position="开发",
                tier="small",
                apply_url="javascript:alert(document.domain)",
                status="open",
            )
        )
        db.commit()

    listed = admin_client.get("/api/jobs")
    assert listed.status_code == 200
    legacy = next(job for job in listed.json() if job["company"] == "历史数据")
    assert legacy["apply_url"] is None


def test_job_import_discards_non_https_urls():
    from app.seed.import_jobs import build_job

    job = build_job(
        {
            "company": "导入公司",
            "role": "开发",
            "apply_url": "javascript:alert(1)",
        },
        today=date(2026, 1, 1),
    )
    assert job.apply_url is None


def test_job_import_replaces_jobs_and_clears_tracks(admin_client):
    from sqlalchemy import select

    from app import db as dbmod
    from app.models import Job, JobTrack, User
    from app.seed.import_jobs import replace_jobs

    with dbmod.SessionLocal() as db:
        admin = db.scalar(select(User).where(User.username == "admin"))
        assert admin is not None
        old_job = Job(company="旧公司", position="旧岗位", tier="small", status="open")
        db.add(old_job)
        db.flush()
        db.add(JobTrack(user_id=admin.id, job_id=old_job.id, status="applied"))
        db.commit()
        db.expunge_all()

        inserted = replace_jobs(
            db,
            [{"company": "新公司", "role": "新岗位", "apply_url": "https://example.com"}],
            today=date(2026, 1, 1),
        )
        db.commit()

        assert inserted == 1
        assert db.query(JobTrack).count() == 0
        jobs = list(db.scalars(select(Job)).all())
        assert [(job.company, job.position) for job in jobs] == [("新公司", "新岗位")]
