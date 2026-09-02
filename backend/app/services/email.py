import smtplib
from email.message import EmailMessage

from app.config import settings


def send_family_invitation(*, recipient: str, family_name: str, token: str) -> None:
    missing = [
        name for name, value in (
            ("SMTP_HOST", settings.smtp_host),
            ("SMTP_USERNAME", settings.smtp_username),
            ("SMTP_PASSWORD", settings.smtp_password),
            ("SMTP_FROM_EMAIL", settings.smtp_from_email),
        ) if not value
    ]
    if missing:
        raise RuntimeError(f"Email delivery is not configured: missing {', '.join(missing)}")

    invite_url = f"{settings.frontend_url.rstrip('/')}/invite/{token}"
    message = EmailMessage()
    message["Subject"] = "Byli jste pozváni do rodiny na FamilyQuest"
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message.set_content(
        f"Byli jste pozváni do rodiny {family_name} v aplikaci FamilyQuest.\n\n"
        f"Přijmout pozvánku: {invite_url}\n"
    )
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
        if settings.smtp_use_tls:
            server.starttls()
        server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)
