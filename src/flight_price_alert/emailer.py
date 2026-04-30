from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage


def send_email(subject: str, body: str) -> None:
    host = _env("SMTP_HOST")
    port = int(os.environ.get("SMTP_PORT", "587"))
    username = _env("SMTP_USERNAME")
    password = _env("SMTP_PASSWORD")
    sender = _env("EMAIL_FROM")
    recipient = _env("EMAIL_TO")

    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(host, port) as smtp:
        smtp.starttls()
        smtp.login(username, password)
        smtp.send_message(message)


def _env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value
