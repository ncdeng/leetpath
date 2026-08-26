from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from pydantic import field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_admin
from app.models import Job, JobTrack, User, utcnow
from app.urls import safe_https_url, validate_https_url

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobCreate(BaseModel):
    company: str
    position: str
    tier: Literal["big", "mid", "small"] = "small"
    batch: str | None = None
    open_at: date | None = None
    deadline_at: date | None = None
    jd_text: str | None = None
    apply_url: str | None = None
    status: Literal["open", "closed"] = "open"

    _https_apply_url = field_validator("apply_url")(validate_https_url)


class JobUpdate(BaseModel):
    company: str | None = None
    position: str | None = None
    tier: Literal["big", "mid", "small"] | None = None
    batch: str | None = None
    open_at: date | None = None
    deadline_at: date | None = None
    jd_text: str | None = None
    apply_url: str | None = None
    status: Literal["open", "closed"] | None = None

    _https_apply_url = field_validator("apply_url")(validate_https_url)

    @field_validator("company", "position", "tier", "status")
    @classmethod
    def required_fields_cannot_be_null(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("必填字段不能为 null")
        return value


class JobOut(BaseModel):
    id: int
    company: str
    position: str
    tier: str
    batch: str | None
    open_at: date | None
    deadline_at: date | None
    jd_text: str | None
    apply_url: str | None
    status: str
    created_at: datetime
    days_left: int | None


def job_out(job: Job) -> JobOut:
    days_left = None
    if job.deadline_at is not None:
        days_left = (job.deadline_at - date.today()).days
    return JobOut(
        id=job.id,
        company=job.company,
        position=job.position,
        tier=job.tier,
        batch=job.batch,
        open_at=job.open_at,
        deadline_at=job.deadline_at,
        jd_text=job.jd_text,
        apply_url=safe_https_url(job.apply_url),
        status=job.status,
        created_at=job.created_at,
        days_left=days_left,
    )


@router.get("")
def list_jobs(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[JobOut]:
    jobs = list(
        db.scalars(select(Job).order_by(Job.deadline_at.asc().nulls_last(), Job.id.asc())).all()
    )
    return [job_out(j) for j in jobs]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_job(
    body: JobCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> JobOut:
    job = Job(**body.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    return job_out(job)


@router.put("/{job_id}")
def update_job(
    job_id: int,
    body: JobUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> JobOut:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="岗位不存在")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(job, key, value)
    db.commit()
    db.refresh(job)
    return job_out(job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="岗位不存在")
    db.delete(job)
    db.commit()


TRACK_STATUSES = {"applied", "test", "interview", "offer", "rejected"}


class TrackIn(BaseModel):
    status: str  # TRACK_STATUSES 之一；"none" 表示清除标记


@router.get("/track")
def list_tracks(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[int, str]:
    rows = db.execute(
        select(JobTrack.job_id, JobTrack.status).where(JobTrack.user_id == user.id)
    ).all()
    return {job_id: st for job_id, st in rows}


@router.put("/{job_id}/track")
def set_track(
    job_id: int,
    body: TrackIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    if db.get(Job, job_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="岗位不存在")
    track = db.get(JobTrack, (user.id, job_id))
    if body.status == "none":
        if track is not None:
            db.delete(track)
            db.commit()
        return {"status": "none"}
    if body.status not in TRACK_STATUSES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="非法状态")
    if track is None:
        track = JobTrack(user_id=user.id, job_id=job_id, status=body.status)
        db.add(track)
    else:
        track.status = body.status
        track.updated_at = utcnow()
    db.commit()
    return {"status": body.status}
