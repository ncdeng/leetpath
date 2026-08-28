from __future__ import annotations

import hashlib
import random
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import QuizQuestion, QuizRecord, QuizSolveEvent, User, utcnow

router = APIRouter(prefix="/quiz", tags=["quiz"])


def _normalize_answer(
    ans: str,
    *,
    q_type: str | None = None,
    options: dict[str, str] | None = None,
) -> str:
    """标准化答案字符串以进行健壮比对。判断题按选项原文解释 A/B，不写死 A=正确。"""
    raw = ans.strip()
    folded = raw.upper()
    opts = options or {}
    is_judge = q_type == "judge" or (
        opts and set(opts.values()) <= {"正确", "错误"} and set(opts) <= {"A", "B"}
    )
    if is_judge:
        if folded in opts:
            text = str(opts[folded]).strip()
            if text in ("正确", "对"):
                return "正确"
            if text in ("错误", "错"):
                return "错误"
            return text
        if raw in ("正确", "对") or folded in ("T", "TRUE"):
            return "正确"
        if raw in ("错误", "错") or folded in ("F", "FALSE"):
            return "错误"
        return raw
    if folded in ("正确", "对", "T", "TRUE"):
        return "正确"
    if folded in ("错误", "错", "F", "FALSE"):
        return "错误"
    if len(folded) > 1 and all(c in "ABCD" for c in folded):
        return "".join(sorted(folded))
    return folded


VIEWED_OPEN_ANSWER = "viewed"


def _options_dict(raw: Any) -> dict[str, str]:
    if isinstance(raw, dict):
        return {str(k): str(v) for k, v in raw.items()}
    return {}


def _tags_list(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(t) for t in raw]
    return []


def _has_skip_tag(q: QuizQuestion) -> bool:
    return any(t.lower() == "skip" for t in _tags_list(q.tags))


def _is_open_revealed(q: QuizQuestion, rec: QuizRecord | None) -> bool:
    if rec is None:
        return False
    if q.type == "open":
        return rec.user_answer == VIEWED_OPEN_ANSWER
    return True


class BankItem(BaseModel):
    bank: str
    category: str
    total: int
    answered: int
    correct: int
    wrong: int


class QuizQuestionItem(BaseModel):
    id: int
    bank: str
    category: str
    type: str
    ordinal: int
    stem: str
    options: dict[str, str]
    tags: list[str] = []
    answer_status: str | None = None
    is_answered: bool
    is_correct: bool | None = None
    user_answer: str | None = None
    is_favorite: bool = False
    is_slashed: bool = False
    wrong_count: int = 0
    attempts_count: int = 0
    answer: str | None = None  # 已答/已揭晓时暴露；问答题不给字母答案
    analysis: str | None = None  # 已答/已揭晓时暴露；问答题为草稿


class QuizAnswerIn(BaseModel):
    user_answer: str


class QuizAnswerOut(BaseModel):
    id: int
    is_correct: bool
    correct_answer: str
    analysis: str
    user_answer: str
    wrong_count: int
    attempts_count: int
    is_slashed: bool


class FavoriteIn(BaseModel):
    favorite: bool | None = None


class SlashIn(BaseModel):
    slashed: bool = True


class QuizStats(BaseModel):
    total_questions: int
    answered_count: int
    correct_count: int
    wrong_count: int
    slashed_count: int
    favorite_count: int
    accuracy_rate: float
    today_count: int


def _has_answered(rec: QuizRecord | None) -> bool:
    """收藏/斩题可以建记录，但不能当成已作答。"""
    return rec is not None and rec.attempts_count > 0


class QuizRevealOut(BaseModel):
    id: int
    analysis: str
    answer_status: str = "draft"
    attempts_count: int
    is_answered: bool = True


def _question_item(q_obj: QuizQuestion, rec: QuizRecord | None) -> QuizQuestionItem:
    if q_obj.type == "open":
        is_answered = _is_open_revealed(q_obj, rec)
    else:
        is_answered = _has_answered(rec)
    return QuizQuestionItem(
        id=q_obj.id,
        bank=q_obj.bank,
        category=q_obj.category or "综合理论",
        type=q_obj.type,
        ordinal=q_obj.ordinal,
        stem=q_obj.stem,
        options=_options_dict(q_obj.options),
        tags=_tags_list(q_obj.tags),
        answer_status="draft" if q_obj.type == "open" else None,
        is_answered=is_answered,
        is_correct=rec.is_correct if is_answered and q_obj.type != "open" else None,
        user_answer=rec.user_answer if is_answered else None,
        is_favorite=rec.is_favorite if rec else False,
        is_slashed=rec.is_slashed if rec else False,
        wrong_count=rec.wrong_count if rec else 0,
        attempts_count=rec.attempts_count if rec else 0,
        answer=q_obj.answer if is_answered and q_obj.type != "open" else None,
        analysis=q_obj.analysis if is_answered else None,
    )


def _preference_record(
    *,
    user_id: int,
    question_id: int,
    is_favorite: bool = False,
    is_slashed: bool = False,
) -> QuizRecord:
    return QuizRecord(
        user_id=user_id,
        question_id=question_id,
        is_correct=False,
        user_answer="",
        attempts_count=0,
        wrong_count=0,
        is_favorite=is_favorite,
        is_slashed=is_slashed,
    )


@router.get("/banks")
def list_banks(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[BankItem]:
    """获取全部专题列表与当前用户的学习进度"""
    # 统计所有题目的 bank 与 category
    questions = db.scalars(select(QuizQuestion).order_by(QuizQuestion.id)).all()
    user_records = {
        r.question_id: r
        for r in db.scalars(
            select(QuizRecord).where(QuizRecord.user_id == user.id)
        ).all()
    }

    bank_map: dict[str, dict[str, Any]] = {}
    for q in questions:
        if q.bank not in bank_map:
            bank_map[q.bank] = {
                "bank": q.bank,
                "category": q.category or "综合理论",
                "total": 0,
                "answered": 0,
                "correct": 0,
                "wrong": 0,
            }
        b = bank_map[q.bank]
        b["total"] += 1
        rec = user_records.get(q.id)
        if q.type == "open":
            if _is_open_revealed(q, rec):
                b["answered"] += 1
            continue
        if _has_answered(rec):
            b["answered"] += 1
            if rec.is_correct:
                b["correct"] += 1
            else:
                b["wrong"] += 1

    return [BankItem(**b) for b in bank_map.values()]


@router.get("/questions")
def list_questions(
    bank: str | None = None,
    category: str | None = None,
    type: str | None = None,
    status: str | None = Query(None, description="all / wrong / unanswered / correct / favorited / slashed"),
    q: str | None = None,
    random_order: bool = False,
    exclude_skipped: bool = False,
    exclude_open: bool = False,
    limit: int | None = Query(
        None,
        ge=0,
        description="不传或 0 返回全部匹配题；正整数为分页条数。刷题不要截断。",
    ),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """按条件筛选题目列表"""
    stmt = select(QuizQuestion)
    if bank:
        stmt = stmt.where(QuizQuestion.bank == bank)
    if category:
        stmt = stmt.where(QuizQuestion.category == category)
    if type:
        stmt = stmt.where(QuizQuestion.type == type)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(QuizQuestion.stem.ilike(like), QuizQuestion.bank.ilike(like)))

    questions = list(db.scalars(stmt.order_by(QuizQuestion.id)).all())
    if exclude_skipped:
        questions = [q_item for q_item in questions if not _has_skip_tag(q_item)]
    if exclude_open:
        questions = [q_item for q_item in questions if q_item.type != "open"]

    # 用户答题记录
    user_records = {
        r.question_id: r
        for r in db.scalars(
            select(QuizRecord).where(QuizRecord.user_id == user.id)
        ).all()
    }

    # 根据用户状态过滤
    filtered: list[QuizQuestion] = []
    for q_item in questions:
        rec = user_records.get(q_item.id)
        answered = _has_answered(rec)
        if status == "wrong":
            # 错题本：做错过且未斩题；问答题不进错题本
            if answered and rec and (not rec.is_correct) and (not rec.is_slashed) and q_item.type != "open":
                filtered.append(q_item)
        elif status == "unanswered":
            if q_item.type == "open":
                if not _is_open_revealed(q_item, rec):
                    filtered.append(q_item)
            elif not answered:
                filtered.append(q_item)
        elif status == "correct":
            if answered and rec and rec.is_correct and q_item.type != "open":
                filtered.append(q_item)
        elif status == "favorited":
            if rec and rec.is_favorite:
                filtered.append(q_item)
        elif status == "slashed":
            if rec and rec.is_slashed:
                filtered.append(q_item)
        else:
            filtered.append(q_item)

    total_matched = len(filtered)

    if random_order:
        random.shuffle(filtered)
    if limit:
        paged = filtered[offset : offset + limit]
    else:
        paged = filtered[offset:]

    items = [_question_item(q_obj, user_records.get(q_obj.id)) for q_obj in paged]

    return {
        "total": total_matched,
        "offset": offset,
        "limit": limit if limit else len(items),
        "items": items,
    }


@router.get("/today")
def today_path(
    tz_offset: int = Query(0, ge=-720, le=840, description="客户端相对 UTC 的分钟偏移，北京时间为 480"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """今日路径：按本地日期稳定抽题，跳过 tags 含 skip 的题（含 skip+java）。"""
    offset = timedelta(minutes=tz_offset)
    local_date = (utcnow() + offset).date().isoformat()

    questions = list(db.scalars(select(QuizQuestion).order_by(QuizQuestion.id)).all())
    pool = [q_obj for q_obj in questions if not _has_skip_tag(q_obj)]
    user_records = {
        r.question_id: r
        for r in db.scalars(select(QuizRecord).where(QuizRecord.user_id == user.id)).all()
    }

    seed_src = f"{user.id}:{local_date}:quiz-today"
    seed = int(hashlib.sha256(seed_src.encode()).hexdigest()[:16], 16)
    rng = random.Random(seed)
    rng.shuffle(pool)

    def _unanswered(q_obj: QuizQuestion) -> bool:
        rec = user_records.get(q_obj.id)
        if q_obj.type == "open":
            return not _is_open_revealed(q_obj, rec)
        return rec is None

    unanswered = [q_obj for q_obj in pool if _unanswered(q_obj)]
    answered = [q_obj for q_obj in pool if not _unanswered(q_obj)]
    ordered = unanswered + answered
    picked = ordered[:limit]
    return {
        "date": local_date,
        "total": len(picked),
        "limit": limit,
        "items": [_question_item(q_obj, user_records.get(q_obj.id)) for q_obj in picked],
    }


@router.get("/questions/{question_id}")
def get_question(
    question_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> QuizQuestionItem:
    """获取单个题目详情"""
    q_obj = db.get(QuizQuestion, question_id)
    if q_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在")

    rec = db.get(QuizRecord, (user.id, question_id))
    return _question_item(q_obj, rec)


@router.post("/questions/{question_id}/answer")
def submit_answer(
    question_id: int,
    body: QuizAnswerIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> QuizAnswerOut:
    """提交答案并进行即时判分与解析返回"""
    q_obj = db.get(QuizQuestion, question_id)
    if q_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在")
    if q_obj.type == "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="问答题请揭晓草稿，不按选项判分",
        )

    opts = q_obj.options or {}
    norm_user = _normalize_answer(body.user_answer, q_type=q_obj.type, options=opts)
    norm_correct = _normalize_answer(q_obj.answer, q_type=q_obj.type, options=opts)
    is_correct = norm_user == norm_correct

    rec = db.get(QuizRecord, (user.id, question_id))
    if rec is None:
        rec = QuizRecord(
            user_id=user.id,
            question_id=question_id,
            is_correct=is_correct,
            user_answer=body.user_answer.strip(),
            attempts_count=1,
            wrong_count=0 if is_correct else 1,
            is_favorite=False,
            is_slashed=False,
            updated_at=utcnow(),
        )
        db.add(rec)
    else:
        rec.is_correct = is_correct
        rec.user_answer = body.user_answer.strip()
        rec.attempts_count += 1
        if not is_correct:
            rec.wrong_count += 1
            rec.is_slashed = False  # 再次做错重新回到错题本
        rec.updated_at = utcnow()

    if is_correct and db.get(QuizSolveEvent, (user.id, question_id)) is None:
        db.add(QuizSolveEvent(user_id=user.id, question_id=question_id, solved_at=utcnow()))

    db.commit()
    db.refresh(rec)

    return QuizAnswerOut(
        id=q_obj.id,
        is_correct=is_correct,
        correct_answer=q_obj.answer,
        analysis=q_obj.analysis,
        user_answer=body.user_answer.strip(),
        wrong_count=rec.wrong_count,
        attempts_count=rec.attempts_count,
        is_slashed=rec.is_slashed,
    )


@router.post("/questions/{question_id}/favorite")
def toggle_favorite(
    question_id: int,
    body: FavoriteIn | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """切换或设置题目收藏状态"""
    q_obj = db.get(QuizQuestion, question_id)
    if q_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在")

    rec = db.get(QuizRecord, (user.id, question_id))
    if rec is None:
        fav = True if (body is None or body.favorite is None) else body.favorite
        rec = _preference_record(user_id=user.id, question_id=question_id, is_favorite=fav)
        db.add(rec)
    else:
        if body is None or body.favorite is None:
            rec.is_favorite = not rec.is_favorite
        else:
            rec.is_favorite = body.favorite

    db.commit()
    return {"id": question_id, "is_favorite": rec.is_favorite}


@router.post("/questions/{question_id}/slash")
def slash_question(
    question_id: int,
    body: SlashIn | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """斩题 / 从错题本移除"""
    q_obj = db.get(QuizQuestion, question_id)
    if q_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在")

    rec = db.get(QuizRecord, (user.id, question_id))
    slashed = True if body is None else body.slashed
    if rec is None:
        rec = _preference_record(user_id=user.id, question_id=question_id, is_slashed=slashed)
        db.add(rec)
    else:
        rec.is_slashed = slashed

    db.commit()
    return {"id": question_id, "is_slashed": rec.is_slashed}


@router.post("/questions/{question_id}/reveal")
def reveal_open_answer(
    question_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> QuizRevealOut:
    """揭晓问答题草稿答案（不判分）。"""
    q_obj = db.get(QuizQuestion, question_id)
    if q_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在")
    if q_obj.type != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅问答题可揭晓草稿",
        )

    rec = db.get(QuizRecord, (user.id, question_id))
    if rec is None:
        rec = QuizRecord(
            user_id=user.id,
            question_id=question_id,
            is_correct=True,
            user_answer=VIEWED_OPEN_ANSWER,
            attempts_count=1,
            wrong_count=0,
            is_favorite=False,
            is_slashed=False,
            updated_at=utcnow(),
        )
        db.add(rec)
    else:
        rec.user_answer = VIEWED_OPEN_ANSWER
        rec.is_correct = True
        rec.attempts_count = max(rec.attempts_count, 1)
        rec.updated_at = utcnow()

    db.commit()
    db.refresh(rec)
    return QuizRevealOut(
        id=q_obj.id,
        analysis=q_obj.analysis or "",
        answer_status="draft",
        attempts_count=rec.attempts_count,
        is_answered=True,
    )


@router.get("/stats")
def get_quiz_stats(
    tz_offset: int = Query(0, ge=-720, le=840, description="客户端相对 UTC 的分钟偏移，北京时间为 480"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> QuizStats:
    """获取用户在客观题题库上的刷题概览与战报统计"""
    total_q = db.scalar(select(func.count(QuizQuestion.id))) or 0
    records = list(
        db.scalars(select(QuizRecord).where(QuizRecord.user_id == user.id)).all()
    )
    type_by_id = {
        q_id: q_type
        for q_id, q_type in db.execute(select(QuizQuestion.id, QuizQuestion.type)).all()
    }

    answered_records = [r for r in records if _has_answered(r)]
    graded = [r for r in answered_records if type_by_id.get(r.question_id) != "open"]
    answered_count = len(answered_records)
    correct_count = sum(1 for r in graded if r.is_correct)
    wrong_count = sum(1 for r in graded if not r.is_correct and not r.is_slashed)
    slashed_count = sum(1 for r in records if r.is_slashed)
    favorite_count = sum(1 for r in records if r.is_favorite)

    accuracy_rate = (
        round((correct_count / len(graded)) * 100, 1) if graded else 0.0
    )

    # 今日刷题数只统计实际作答；收藏/斩题不改 updated_at，避免污染。
    offset = timedelta(minutes=tz_offset)
    local_now = utcnow() + offset
    today_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0) - offset
    today_count = sum(1 for r in answered_records if r.updated_at >= today_start)

    return QuizStats(
        total_questions=total_q,
        answered_count=answered_count,
        correct_count=correct_count,
        wrong_count=wrong_count,
        slashed_count=slashed_count,
        favorite_count=favorite_count,
        accuracy_rate=accuracy_rate,
        today_count=today_count,
    )
