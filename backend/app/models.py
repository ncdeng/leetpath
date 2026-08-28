from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

SUBMISSION_STATUSES = ("pending", "judging", "AC", "WA", "TLE", "MLE", "CE", "RE", "IE")
LANGUAGES = ("python3", "cpp")
IO_MODES = ("acm", "leetcode")
DIFFICULTIES = ("easy", "medium", "hard")
SOURCES = ("hot100", "mianjing")


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    avatar_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    token_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    submissions: Mapped[list["Submission"]] = relationship(back_populates="user")


class Invite(Base):
    __tablename__ = "invites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    used_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Problem(Base):
    __tablename__ = "problems"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    leetcode_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    difficulty: Mapped[str] = mapped_column(String(16))
    source: Mapped[str] = mapped_column(String(16))
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    statement_md: Mapped[str] = mapped_column(Text)
    solution_md: Mapped[str | None] = mapped_column(Text, nullable=True)  # 背题模式题解
    time_limit_ms: Mapped[int] = mapped_column(Integer, default=5000)
    memory_limit_mb: Mapped[int] = mapped_column(Integer, default=256)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    leetcode_spec: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    testcases: Mapped[list["Testcase"]] = relationship(
        back_populates="problem", cascade="all, delete-orphan"
    )
    submissions: Mapped[list["Submission"]] = relationship(back_populates="problem")


class Testcase(Base):
    __tablename__ = "testcases"
    __table_args__ = (UniqueConstraint("problem_id", "ordinal"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    input: Mapped[str] = mapped_column(Text)
    expected_output: Mapped[str] = mapped_column(Text)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False)

    problem: Mapped[Problem] = relationship(back_populates="testcases")


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"))
    language: Mapped[str] = mapped_column(String(16))
    io_mode: Mapped[str] = mapped_column(String(16), default="acm", server_default="acm")
    code: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    detail: Mapped[list | dict | None] = mapped_column(JSON, nullable=True)
    compile_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    runtime_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    judged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    user: Mapped[User] = relationship(back_populates="submissions")
    problem: Mapped[Problem] = relationship(back_populates="submissions")


class ReviewCard(Base):
    """背题模式的记忆状态：每个用户每题一条。"""

    __tablename__ = "review_cards"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), primary_key=True)
    remembered: Mapped[bool] = mapped_column(Boolean, default=False)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Draft(Base):
    __tablename__ = "drafts"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), primary_key=True)
    language: Mapped[str] = mapped_column(String(16), primary_key=True)
    code: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class JobTrack(Base):
    """求职进度标记：每个用户每个岗位一条（已投/笔试/面试/Offer/结束）。"""

    __tablename__ = "job_tracks"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True)
    status: Mapped[str] = mapped_column(String(16))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company: Mapped[str] = mapped_column(String(128))
    position: Mapped[str] = mapped_column(String(128))
    tier: Mapped[str] = mapped_column(String(16), default="small", index=True)  # big/mid/small
    batch: Mapped[str | None] = mapped_column(String(64), nullable=True)
    open_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    deadline_at: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    jd_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    apply_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


QUIZ_TYPES = ("single", "multiple", "judge", "open")


class QuizQuestion(Base):
    """八股题库（单选/多选/判断/问答）"""
    __tablename__ = "quiz_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bank: Mapped[str] = mapped_column(String(128), index=True)  # 专题名，例如 "AI Agent 核心概念与架构"
    category: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)  # 大类分类
    type: Mapped[str] = mapped_column(String(16), index=True)  # single / multiple / judge / open
    ordinal: Mapped[int] = mapped_column(Integer)  # 题号
    stem: Mapped[str] = mapped_column(Text)  # 题干
    options: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)  # {"A": "...", "B": "..."}；问答题为空对象
    answer: Mapped[str] = mapped_column(String(32))  # "B", "ACD", "正确", "错误"；问答题为空串
    analysis: Mapped[str] = mapped_column(Text)  # 客观题解析；问答题存草稿答案
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)  # 如 skip / java；含 skip 的题默认不进今日路径
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    records: Mapped[list["QuizRecord"]] = relationship(
        back_populates="question", cascade="all, delete-orphan"
    )


class QuizRecord(Base):
    """用户答题记录与错题/收藏状态"""
    __tablename__ = "quiz_records"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("quiz_questions.id"), primary_key=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    user_answer: Mapped[str] = mapped_column(String(32))  # 用户最后提交的答案
    attempts_count: Mapped[int] = mapped_column(Integer, default=1)
    wrong_count: Mapped[int] = mapped_column(Integer, default=0)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    is_slashed: Mapped[bool] = mapped_column(Boolean, default=False)  # 斩题标记（移出错题本）
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    user: Mapped[User] = relationship()
    question: Mapped[QuizQuestion] = relationship(back_populates="records")


class QuizSolveEvent(Base):
    """用户首次答对八股题的事实事件。"""

    __tablename__ = "quiz_solve_events"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("quiz_questions.id"), primary_key=True)
    solved_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class StudySession(Base):
    """按用户、客户端会话和本地自然日累计的活跃时长。"""

    __tablename__ = "study_sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    surface: Mapped[str] = mapped_column(String(16))
    day: Mapped[date] = mapped_column(Date, index=True)
    active_seconds: Mapped[int] = mapped_column(Integer, default=0)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    __table_args__ = (UniqueConstraint("user_id", "session_id", "day"),)


class SystemSetting(Base):
    """系统全局配置（管理员在 Web 后台动态配置，如共享 AI 密钥等）"""
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

