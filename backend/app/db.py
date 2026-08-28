from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parent.parent

engine: Engine | None = None
SessionLocal: sessionmaker[Session] | None = None


class Base(DeclarativeBase):
    pass


def resolve_database_url(url: str) -> str:
    if not url.startswith("sqlite:///"):
        return url
    rest = url[len("sqlite:///"):]
    if rest == ":memory:" or rest.startswith(":memory:"):
        return url
    path = Path(rest)
    if not path.is_absolute():
        path = BACKEND_ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return "sqlite:///" + path.resolve().as_posix()


def _sqlite_connect(dbapi_conn, _connection_record) -> None:
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def configure_db(database_url: str | None = None) -> Engine:
    global engine, SessionLocal
    if engine is not None:
        engine.dispose()
        engine = None
        SessionLocal = None

    settings = get_settings()
    url = resolve_database_url(database_url or settings.DATABASE_URL)
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    engine = create_engine(url, connect_args=connect_args, future=True)
    if url.startswith("sqlite"):
        event.listen(engine, "connect", _sqlite_connect)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return engine


def _ensure_job_tracks_delete_cascade(conn) -> None:
    """旧库 job_tracks.job_id 外键补 ON DELETE CASCADE（SQLite 需重建表）。"""
    track_rows = conn.execute(text("PRAGMA table_info(job_tracks)")).fetchall()
    if not track_rows:
        return
    foreign_keys = conn.execute(text("PRAGMA foreign_key_list(job_tracks)")).fetchall()
    has_cascade = any(
        row[2] == "jobs"
        and row[3] == "job_id"
        and row[4] == "id"
        and str(row[6]).upper() == "CASCADE"
        for row in foreign_keys
    )
    if has_cascade:
        return

    temporary_rows = conn.execute(
        text("PRAGMA table_info(job_tracks__cascade_new)")
    ).fetchall()
    if temporary_rows:
        raise RuntimeError("检测到遗留的 job_tracks__cascade_new 表，停止自动迁移")

    conn.execute(
        text(
            """
            CREATE TABLE job_tracks__cascade_new (
                user_id INTEGER NOT NULL,
                job_id INTEGER NOT NULL,
                status VARCHAR(16) NOT NULL,
                updated_at DATETIME NOT NULL,
                PRIMARY KEY (user_id, job_id),
                FOREIGN KEY(user_id) REFERENCES users (id),
                FOREIGN KEY(job_id) REFERENCES jobs (id) ON DELETE CASCADE
            )
            """
        )
    )
    conn.execute(
        text(
            """
            INSERT INTO job_tracks__cascade_new (user_id, job_id, status, updated_at)
            SELECT user_id, job_id, status, updated_at FROM job_tracks
            """
        )
    )
    conn.execute(text("DROP TABLE job_tracks"))
    conn.execute(text("ALTER TABLE job_tracks__cascade_new RENAME TO job_tracks"))
    violations = conn.execute(text("PRAGMA foreign_key_check(job_tracks)")).fetchall()
    if violations:
        raise RuntimeError(f"job_tracks 外键迁移后校验失败: {violations}")


def _apply_schema_updates(conn) -> None:
    rows = conn.execute(text("PRAGMA table_info(problems)")).fetchall()
    if rows:
        cols = {row[1] for row in rows}
        if "leetcode_id" not in cols:
            conn.execute(text("ALTER TABLE problems ADD COLUMN leetcode_id INTEGER"))
        if "leetcode_spec" not in cols:
            conn.execute(text("ALTER TABLE problems ADD COLUMN leetcode_spec JSON"))
    submission_rows = conn.execute(text("PRAGMA table_info(submissions)")).fetchall()
    submission_cols = {row[1] for row in submission_rows}
    if submission_rows and "judged_at" not in submission_cols:
        conn.execute(text("ALTER TABLE submissions ADD COLUMN judged_at DATETIME"))
    if submission_rows and "io_mode" not in submission_cols:
        conn.execute(text("ALTER TABLE submissions ADD COLUMN io_mode VARCHAR(16) DEFAULT 'acm'"))
    user_rows = conn.execute(text("PRAGMA table_info(users)")).fetchall()
    user_cols = {row[1] for row in user_rows}
    if user_rows:
        if "avatar_path" not in user_cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN avatar_path VARCHAR(255)"))
        if "avatar_updated_at" not in user_cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN avatar_updated_at DATETIME"))
        if "token_version" not in user_cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN token_version INTEGER DEFAULT 0"))
    quiz_rows = conn.execute(text("PRAGMA table_info(quiz_questions)")).fetchall()
    if quiz_rows:
        quiz_cols = {row[1] for row in quiz_rows}
        if "tags" not in quiz_cols:
            conn.execute(text("ALTER TABLE quiz_questions ADD COLUMN tags JSON"))
    _ensure_job_tracks_delete_cascade(conn)


def ensure_schema(bind: Engine | None = None) -> None:
    """为已有 SQLite 库补列和约束。create_all 不会 ALTER 现有表。"""
    eng = bind if bind is not None else engine
    if eng is None or eng.dialect.name != "sqlite":
        return
    with eng.connect() as conn:
        # sqlite3 legacy transaction control 不会在 DDL 前自动 BEGIN；显式写锁
        # 保证重建 job_tracks 的 CREATE/COPY/DROP/RENAME 能整体回滚。
        conn.exec_driver_sql("BEGIN IMMEDIATE")
        try:
            _apply_schema_updates(conn)
        except Exception:
            conn.rollback()
            raise
        else:
            conn.commit()


def get_db() -> Generator[Session, None, None]:
    if SessionLocal is None:
        configure_db()
    assert SessionLocal is not None
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
