import json
import logging
import os
from threading import Thread
from typing import Any

from firebase_admin import credentials, get_app, initialize_app, messaging
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.models import PushToken

logger = logging.getLogger(__name__)


def _firebase_app():
    raw_credentials = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if not raw_credentials:
        return None
    try:
        return get_app()
    except ValueError:
        try:
            return initialize_app(credentials.Certificate(json.loads(raw_credentials)))
        except (ValueError, TypeError, json.JSONDecodeError):
            logger.exception("Invalid FIREBASE_SERVICE_ACCOUNT_JSON configuration")
            return None


def _send_push(user_id: str, title: str, message: str) -> None:
    app = _firebase_app()
    if app is None:
        return
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        tokens = [item.token for item in db.query(PushToken).filter(PushToken.user_id == user_id).all()]
        if tokens:
            messaging.send_each_for_multicast(
                messaging.MulticastMessage(
                    tokens=tokens,
                    notification=messaging.Notification(title=title, body=message),
                    android=messaging.AndroidConfig(
                        priority="high",
                        notification=messaging.AndroidNotification(
                            channel_id="familyquest",
                            visibility="public",
                            sound="default",
                        ),
                    ),
                ),
                app=app,
            )
    except Exception:
        logger.exception("FCM push delivery failed for user %s", user_id)
    finally:
        db.close()


def queue_push(user_id: str, title: str, message: str) -> None:
    Thread(target=_send_push, args=(user_id, title, message), daemon=True).start()


@event.listens_for(Session, "after_commit")
def send_committed_pushes(session: Session) -> None:
    pushes: list[tuple[str, str, str]] = session.info.pop("pending_pushes", [])
    for user_id, title, message in pushes:
        queue_push(user_id, title, message)


def queue_notification_push(session: Session, user_id: str, title: str, message: str) -> None:
    session.info.setdefault("pending_pushes", []).append((user_id, title, message))
