"""Overdue-approval reminders: periodic scan + WeCom push (best effort)."""
import logging
from datetime import timedelta, timezone

from sqlalchemy.orm import Session

from app.models import ApprovalTask, ApprovalTicket, User, utcnow

logger = logging.getLogger(__name__)

REMIND_INTERVAL_HOURS = 4  # re-remind the same task at most every 4h


def send_wecom_text(db: Session, user: User, content: str) -> bool:
    """Push a text message via WeCom appchat (only when wecom auth is enabled and
    the user has an external wecom userid)."""
    try:
        from app.services import config_service, wecom_service

        cfg = config_service.wecom_config(db)
        if not cfg.get("enabled") or not user.external_id:
            return False
        token = wecom_service._get_access_token(cfg)
        import httpx

        resp = httpx.post(
            f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}",
            json={
                "touser": user.external_id,
                "msgtype": "text",
                "agentid": int(cfg.get("agent_id") or 0),
                "text": {"content": content},
            },
            timeout=5,
        )
        return resp.json().get("errcode") in (0, None)
    except Exception:
        logger.exception("wecom push failed")
        return False


def _aware(dt):
    """SQLite returns naive datetimes; normalize to UTC-aware before comparing."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def remind_overdue() -> int:
    """Scan pending approval tasks past their deadline and remind (mark reminded_at)."""
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        now = utcnow()
        threshold = now - timedelta(hours=REMIND_INTERVAL_HOURS)
        rows = (
            db.query(ApprovalTask, ApprovalTicket, User)
            .join(ApprovalTicket, ApprovalTask.ticket_id == ApprovalTicket.id)
            .outerjoin(User, ApprovalTask.assignee_id == User.id)
            .filter(ApprovalTask.status == "pending",
                    ApprovalTask.due_at.is_not(None),
                    ApprovalTask.due_at < now,
                    ApprovalTicket.status == "running")
            .all()
        )
        count = 0
        for task, ticket, user in rows:
            if _aware(task.reminded_at) and _aware(task.reminded_at) > threshold:
                continue
            task.reminded_at = now
            count += 1
            if user:
                send_wecom_text(
                    db, user,
                    f"【审批催办】「{ticket.title}」的「{task.node_name}」已超时, 请尽快处理")
        db.commit()
        if count:
            logger.info("reminded %d overdue approval tasks", count)
        return count
    finally:
        db.close()
