"""把 data/leetpath-jobs-YYYYMMDD.json 灌进 jobs 表（全量替换）。

用法（在 backend/ 目录下）：
    python -m app.seed.import_jobs ../data/leetpath-jobs-20260823.json

字段映射（JSON -> Job 模型）：
    company   -> company
    role      -> position
    batch     -> batch
    deadline  -> deadline_at（仅接受 ISO 日期，其余置空，不编造）
    apply_url -> apply_url
    city / degree / open_date / source -> 拼进 jd_text 头部，保留原始信息
    status    -> deadline 已过为 closed，否则 open
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app import db as dbmod
from app.db import Base
from app.models import Job, JobTrack
from app.urls import safe_https_url

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# 公司规模分层：大厂 / 中厂，未列出的归小厂
TIER_BIG = {
    "腾讯", "字节跳动", "阿里巴巴", "蚂蚁", "美团", "百度", "京东", "快手",
    "拼多多", "小米", "滴滴", "华为", "网易互娱", "网易集团/互联网", "网易雷火",
    "腾讯音乐TME", "小红书", "B站", "OPPO", "vivo", "荣耀", "大疆", "米哈游",
    "虾皮Shopee", "淘宝闪购/饿了么", "优酷", "蔚来", "理想",
}
TIER_MID = {
    "得物", "作业帮", "唯品会", "招银网络", "平安银行", "顺丰科技", "多益网络",
    "莉莉丝", "叠纸游戏", "巨人网络", "4399", "影石Insta360", "小鹏", "零跑",
    "元戎启行", "小马智行", "合合信息", "视源CVTE", "乐鑫", "陌陌/心域",
    "挚文集团", "猎聘", "搜狐", "新浪", "携程", "同程", "58同城", "瓜子",
    "旷视", "商汤", "科大讯飞", "地平线", "Momenta", "文远知行", "金山",
}


def classify_tier(company: str) -> str:
    if company in TIER_BIG:
        return "big"
    if company in TIER_MID:
        return "mid"
    return "small"


def build_jd_text(raw: dict) -> str:
    head: list[str] = []
    if raw.get("city"):
        head.append(f"城市：{raw['city']}")
    if raw.get("degree"):
        head.append(f"学历：{raw['degree']}")
    if raw.get("open_date"):
        head.append(f"开投：{raw['open_date']}")
    if raw.get("source"):
        head.append(f"来源：{raw['source']}")
    body = (raw.get("jd_points") or "").strip()
    parts = ["\n".join(head)] if head else []
    if body:
        parts.append(body)
    return "\n\n".join(parts)


def build_job(raw: dict, *, today: date) -> Job:
    deadline_raw = (raw.get("deadline") or "").strip()
    deadline = (
        datetime.strptime(deadline_raw, "%Y-%m-%d").date()
        if ISO_DATE.match(deadline_raw)
        else None
    )
    return Job(
        company=raw["company"].strip(),
        position=raw["role"].strip(),
        tier=classify_tier(raw["company"].strip()),
        batch=(raw.get("batch") or "").strip() or None,
        open_at=None,
        deadline_at=deadline,
        jd_text=build_jd_text(raw) or None,
        apply_url=safe_https_url((raw.get("apply_url") or "").strip() or None),
        status="closed" if deadline and deadline < today else "open",
    )


def replace_jobs(session: Session, raws: list[dict], *, today: date) -> int:
    """全量替换岗位；旧岗位的用户投递记录随之清理。"""
    session.execute(delete(JobTrack))
    session.execute(delete(Job))
    for raw in raws:
        session.add(build_job(raw, today=today))
    return len(raws)


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("用法: python -m app.seed.import_jobs <jobs.json>")
    path = Path(sys.argv[1])
    payload = json.loads(path.read_text(encoding="utf-8"))
    raws = payload["jobs"]

    engine = dbmod.configure_db()
    Base.metadata.create_all(bind=engine)

    today = date.today()
    inserted = 0
    assert dbmod.SessionLocal is not None
    with dbmod.SessionLocal() as session:
        inserted = replace_jobs(session, raws, today=today)
        session.commit()
    print(f"导入完成：{inserted} 条岗位（来源 {path.name}）")


if __name__ == "__main__":
    main()
