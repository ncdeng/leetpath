from app.models import QuizQuestion


def test_quiz_crud_and_practice(admin_client):
    from app import db as dbmod

    with dbmod.SessionLocal() as db:
        db.add(
            QuizQuestion(
                bank="AI Agent 核心概念与架构",
                category="AI Agent 与智能体",
                type="single",
                ordinal=1,
                stem="AI Agent 的大脑通常指什么？",
                options={"A": "数据库", "B": "大语言模型（LLM）", "C": "操作系统", "D": "向量库"},
                answer="B",
                analysis="【正确项】B 正确: LLM 为决策大脑。",
            )
        )
        db.add(
            QuizQuestion(
                bank="AI Agent 核心概念与架构",
                category="AI Agent 与智能体",
                type="judge",
                ordinal=2,
                stem="Chatbot 本质上就是 AI Agent。",
                options={"A": "正确", "B": "错误"},
                answer="错误",
                analysis="【正确项】错误: Chatbot 无自主规划和工具调用。",
            )
        )
        db.commit()

    # 1. 获取 banks 列表
    r = admin_client.get("/api/quiz/banks")
    assert r.status_code == 200
    banks = r.json()
    assert len(banks) == 1
    assert banks[0]["bank"] == "AI Agent 核心概念与架构"
    assert banks[0]["total"] == 2
    assert banks[0]["answered"] == 0

    # 2. 获取题目列表
    r = admin_client.get("/api/quiz/questions?bank=AI Agent 核心概念与架构")
    assert r.status_code == 200
    res = r.json()
    assert res["total"] == 2
    items = res["items"]
    q1_id = items[0]["id"]
    q2_id = items[1]["id"]
    assert items[0]["is_answered"] is False
    assert items[0]["answer"] is None  # 答案未作答时不暴露

    # 3. 作答第一题（回答正确）
    ans_r = admin_client.post(
        f"/api/quiz/questions/{q1_id}/answer", json={"user_answer": "B"}
    )
    assert ans_r.status_code == 200
    ans_body = ans_r.json()
    assert ans_body["is_correct"] is True
    assert ans_body["correct_answer"] == "B"
    assert "LLM 为决策大脑" in ans_body["analysis"]

    # 4. 作答第二题（回答错误）
    ans_r2 = admin_client.post(
        f"/api/quiz/questions/{q2_id}/answer", json={"user_answer": "正确"}
    )
    assert ans_r2.status_code == 200
    assert ans_r2.json()["is_correct"] is False
    assert ans_r2.json()["wrong_count"] == 1

    # 5. 查看错题本筛选
    wrong_r = admin_client.get("/api/quiz/questions?status=wrong")
    assert wrong_r.status_code == 200
    wrong_items = wrong_r.json()["items"]
    assert len(wrong_items) == 1
    assert wrong_items[0]["id"] == q2_id

    # 6. 斩题（从错题本消除）
    slash_r = admin_client.post(f"/api/quiz/questions/{q2_id}/slash", json={"slashed": True})
    assert slash_r.status_code == 200
    assert slash_r.json()["is_slashed"] is True

    # 斩题后再查错题本，应该为空
    wrong_r2 = admin_client.get("/api/quiz/questions?status=wrong")
    assert len(wrong_r2.json()["items"]) == 0

    # 7. 收藏功能
    fav_r = admin_client.post(f"/api/quiz/questions/{q1_id}/favorite")
    assert fav_r.status_code == 200
    assert fav_r.json()["is_favorite"] is True

    fav_list = admin_client.get("/api/quiz/questions?status=favorited")
    assert len(fav_list.json()["items"]) == 1

    # 8. 统计数据
    stats_r = admin_client.get("/api/quiz/stats")
    assert stats_r.status_code == 200
    stats = stats_r.json()
    assert stats["total_questions"] == 2
    assert stats["answered_count"] == 2
    assert stats["correct_count"] == 1
    assert stats["accuracy_rate"] == 50.0
    assert stats["favorite_count"] == 1


def test_quiz_seed_includes_agent_harness_bank():
    from pathlib import Path
    import json

    path = Path(__file__).resolve().parents[1] / "app" / "seed" / "quiz_questions.json"
    questions = json.loads(path.read_text(encoding="utf-8"))
    harness = [q for q in questions if q["bank"] == "Agent Harness 与编码智能体"]
    assert len(harness) >= 20
    assert all(q["category"] == "AI Agent 与智能体" for q in harness)
    stems = " ".join(q["stem"] + q["analysis"] for q in harness)
    for kw in ("Harness", "MCP", "CLAUDE.md", "Skill", "compaction"):
        assert kw in stems
    answers = {q["answer"] for q in harness}
    assert "B" in answers


def test_quiz_seed_excludes_non_agent_scope():
    from pathlib import Path
    import json

    path = Path(__file__).resolve().parents[1] / "app" / "seed" / "quiz_questions.json"
    questions = json.loads(path.read_text(encoding="utf-8"))
    banks = {q["bank"] for q in questions}
    assert "算法与数据结构(机考核心)" not in banks
    assert "算法与数学难题(机考进阶)" not in banks
    assert "半导体工业场景(新凯来专属)" not in banks
    assert "算法与机考" not in {q["category"] for q in questions}

    retired_keys = {
        ("机器学习与深度学习基础", 175),
        ("机器学习与深度学习基础", 176),
        ("杀手题库(二)·强化学习与工程篇", 621),
        ("杀手题库(二)·强化学习与工程篇", 622),
        ("杀手题库(二)·强化学习与工程篇", 623),
        ("杀手题库(二)·强化学习与工程篇", 624),
        ("杀手题库(二)·强化学习与工程篇", 625),
        ("杀手题库(二)·强化学习与工程篇", 631),
    }
    assert {(q["bank"], q["ordinal"]) for q in questions}.isdisjoint(retired_keys)

    blob = "\n".join(q["stem"] for q in questions)
    for needle in ("不可变类型", "浅拷贝", "刻蚀", "FDC", "快速排序最坏", "0-1 背包"):
        assert needle not in blob
    assert "AI Agent" in blob or "Agent" in blob


def test_quiz_loader_prunes_questions_missing_from_default_json(admin_client, tmp_path, monkeypatch):
    import json

    from sqlalchemy import select

    from app import db as dbmod
    from app.models import QuizQuestion, QuizRecord, QuizSolveEvent, User
    from app.seed import quiz_loader
    from app.seed.quiz_loader import load_quiz_questions

    keep = {
        "bank": "AI Agent 核心概念与架构",
        "category": "AI Agent 与智能体",
        "type": "single",
        "ordinal": 1,
        "stem": "AI Agent 的大脑通常指什么？",
        "options": {"A": "数据库", "B": "大语言模型（LLM）", "C": "操作系统", "D": "向量库"},
        "answer": "B",
        "analysis": "【正确项】B",
    }
    seed_path = tmp_path / "quiz_questions.json"
    seed_path.write_text(json.dumps([keep], ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(quiz_loader, "DEFAULT_JSON_PATH", seed_path)

    with dbmod.SessionLocal() as db:
        admin = db.scalar(select(User).where(User.username == "admin"))
        assert admin is not None
        keep_q = QuizQuestion(
            bank=keep["bank"],
            category=keep["category"],
            type=keep["type"],
            ordinal=keep["ordinal"],
            stem=keep["stem"],
            options=keep["options"],
            answer=keep["answer"],
            analysis=keep["analysis"],
        )
        stale_q = QuizQuestion(
            bank="算法与数据结构(机考核心)",
            category="算法与机考",
            type="single",
            ordinal=130,
            stem="数组随机访问的时间复杂度是？",
            options={"A": "O(1)", "B": "O(n)", "C": "O(log n)", "D": "O(n log n)"},
            answer="A",
            analysis="随机访问 O(1)",
        )
        db.add_all([keep_q, stale_q])
        db.flush()
        db.add(
            QuizRecord(
                user_id=admin.id,
                question_id=stale_q.id,
                is_correct=True,
                user_answer="A",
                attempts_count=1,
                wrong_count=0,
            )
        )
        db.add(QuizSolveEvent(user_id=admin.id, question_id=stale_q.id))
        db.commit()
        keep_id, stale_id, uid = keep_q.id, stale_q.id, admin.id

    assert load_quiz_questions() == 1

    with dbmod.SessionLocal() as db:
        assert db.get(QuizQuestion, keep_id) is not None
        assert db.get(QuizQuestion, stale_id) is None
        assert db.get(QuizRecord, (uid, stale_id)) is None
        assert db.get(QuizSolveEvent, (uid, stale_id)) is None
        assert db.scalar(select(QuizQuestion).where(QuizQuestion.bank == "算法与数据结构(机考核心)")) is None


def test_quiz_loader_partial_json_does_not_prune_other_banks(admin_client, tmp_path):
    import json

    from sqlalchemy import select

    from app import db as dbmod
    from app.models import QuizQuestion
    from app.seed.quiz_loader import load_quiz_questions

    with dbmod.SessionLocal() as db:
        db.add(
            QuizQuestion(
                bank="AI Agent 核心概念与架构",
                category="AI Agent 与智能体",
                type="single",
                ordinal=99,
                stem="保留题",
                options={"A": "1", "B": "2"},
                answer="A",
                analysis="x",
            )
        )
        db.commit()

    payload = [
        {
            "bank": "remap-only",
            "category": "t",
            "type": "single",
            "ordinal": 1,
            "stem": "临时导入",
            "options": {"A": "1", "B": "2"},
            "answer": "A",
            "analysis": "x",
        }
    ]
    path = tmp_path / "partial.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    assert load_quiz_questions(path) == 1

    with dbmod.SessionLocal() as db:
        assert db.scalar(
            select(QuizQuestion).where(
                QuizQuestion.bank == "AI Agent 核心概念与架构",
                QuizQuestion.ordinal == 99,
            )
        ) is not None
        assert db.scalar(select(QuizQuestion).where(QuizQuestion.bank == "remap-only")) is not None


def test_unanswered_favorite_and_slash_do_not_reveal_answers_or_pollute_stats(admin_client):
    from datetime import timedelta

    from sqlalchemy import select

    from app import db as dbmod
    from app.models import QuizRecord, User, utcnow

    with dbmod.SessionLocal() as db:
        admin = db.scalar(select(User).where(User.username == "admin"))
        assert admin is not None
        admin_id = admin.id
        favorite = QuizQuestion(
            bank="preference-only",
            category="测试",
            type="single",
            ordinal=1,
            stem="收藏后仍未作答？",
            options={"A": "是", "B": "否"},
            answer="A",
            analysis="收藏不等于作答。",
        )
        slashed = QuizQuestion(
            bank="preference-only",
            category="测试",
            type="judge",
            ordinal=2,
            stem="斩题后仍未作答？",
            options={"A": "正确", "B": "错误"},
            answer="正确",
            analysis="斩题也不等于作答。",
        )
        db.add_all([favorite, slashed])
        db.commit()
        favorite_id, slashed_id = favorite.id, slashed.id

    assert admin_client.post(f"/api/quiz/questions/{favorite_id}/favorite").status_code == 200
    assert admin_client.post(f"/api/quiz/questions/{slashed_id}/slash").status_code == 200

    favorite_item = admin_client.get(f"/api/quiz/questions/{favorite_id}").json()
    slashed_item = admin_client.get(f"/api/quiz/questions/{slashed_id}").json()
    for item in (favorite_item, slashed_item):
        assert item["is_answered"] is False
        assert item["is_correct"] is None
        assert item["user_answer"] is None
        assert item["answer"] is None
        assert item["analysis"] is None
    assert favorite_item["is_favorite"] is True
    assert slashed_item["is_slashed"] is True

    unanswered = admin_client.get(
        "/api/quiz/questions?bank=preference-only&status=unanswered"
    ).json()["items"]
    assert {item["id"] for item in unanswered} == {favorite_id, slashed_id}
    assert admin_client.get("/api/quiz/questions?bank=preference-only&status=wrong").json()["total"] == 0
    assert admin_client.get("/api/quiz/questions?bank=preference-only&status=correct").json()["total"] == 0

    bank = next(
        item for item in admin_client.get("/api/quiz/banks").json()
        if item["bank"] == "preference-only"
    )
    assert bank["answered"] == 0
    assert bank["correct"] == 0
    assert bank["wrong"] == 0

    stats = admin_client.get("/api/quiz/stats").json()
    assert stats["answered_count"] == 0
    assert stats["correct_count"] == 0
    assert stats["wrong_count"] == 0
    assert stats["favorite_count"] == 1
    assert stats["slashed_count"] == 1
    assert stats["today_count"] == 0

    answered = admin_client.post(
        f"/api/quiz/questions/{favorite_id}/answer", json={"user_answer": "B"}
    )
    assert answered.status_code == 200
    assert answered.json()["is_correct"] is False
    refreshed = admin_client.get(f"/api/quiz/questions/{favorite_id}").json()
    assert refreshed["is_answered"] is True
    assert refreshed["answer"] == "A"
    assert refreshed["is_favorite"] is True

    answered_yesterday = utcnow() - timedelta(days=1)
    with dbmod.SessionLocal() as db:
        record = db.get(QuizRecord, (admin_id, favorite_id))
        assert record is not None
        record.updated_at = answered_yesterday
        db.commit()

    assert admin_client.post(
        f"/api/quiz/questions/{favorite_id}/favorite", json={"favorite": False}
    ).status_code == 200
    assert admin_client.post(
        f"/api/quiz/questions/{favorite_id}/slash", json={"slashed": True}
    ).status_code == 200

    with dbmod.SessionLocal() as db:
        record = db.get(QuizRecord, (admin_id, favorite_id))
        assert record is not None
        assert record.updated_at == answered_yesterday
    assert admin_client.get("/api/quiz/stats").json()["today_count"] == 0


def test_quiz_loader_remaps_user_letters_without_resetting_records(admin_client, tmp_path):
    import json

    from app import db as dbmod
    from app.models import QuizQuestion, QuizRecord, User
    from app.seed.quiz_loader import load_quiz_questions

    with dbmod.SessionLocal() as db:
        from sqlalchemy import select

        admin = db.scalar(select(User).where(User.username == "admin"))
        assert admin is not None
        q = QuizQuestion(
            bank="remap-bank",
            category="t",
            type="single",
            ordinal=1,
            stem="大脑？",
            options={"A": "数据库", "B": "大语言模型（LLM）", "C": "操作系统", "D": "向量库"},
            answer="B",
            analysis="【正确项】B",
        )
        db.add(q)
        db.flush()
        db.add(
            QuizRecord(
                user_id=admin.id,
                question_id=q.id,
                is_correct=True,
                user_answer="B",
                attempts_count=1,
                wrong_count=0,
            )
        )
        db.commit()
        qid, uid = q.id, admin.id

    payload = [
        {
            "bank": "remap-bank",
            "category": "t",
            "type": "single",
            "ordinal": 1,
            "stem": "大脑？",
            "options": {
                "A": "大语言模型（LLM）",
                "B": "数据库",
                "C": "操作系统",
                "D": "向量库",
            },
            "answer": "A",
            "analysis": "【正确项】A",
        }
    ]
    path = tmp_path / "quiz.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    assert load_quiz_questions(path) == 1

    with dbmod.SessionLocal() as db:
        rec = db.get(QuizRecord, (uid, qid))
        q = db.get(QuizQuestion, qid)
        assert rec is not None and q is not None
        assert q.answer == "A"
        assert rec.user_answer == "A"
        assert rec.is_correct is True
        assert rec.attempts_count == 1
        assert rec.wrong_count == 0


def test_judge_grades_by_option_text_after_ab_swap(admin_client):
    from app import db as dbmod
    from app.models import QuizQuestion

    with dbmod.SessionLocal() as db:
        q = QuizQuestion(
            bank="judge-swap",
            category="t",
            type="judge",
            ordinal=1,
            stem="Chatbot 就是 Agent。",
            options={"A": "错误", "B": "正确"},
            answer="错误",
            analysis="【正确项】错误",
        )
        db.add(q)
        db.commit()
        qid = q.id

    listed = admin_client.get("/api/quiz/questions?bank=judge-swap").json()["items"]
    assert listed[0]["id"] == qid
    # 点 A（文案是「错误」）应判对，不能再写死 A=正确
    ok = admin_client.post(f"/api/quiz/questions/{qid}/answer", json={"user_answer": "A"})
    assert ok.status_code == 200
    assert ok.json()["is_correct"] is True
    assert ok.json()["correct_answer"] == "错误"
