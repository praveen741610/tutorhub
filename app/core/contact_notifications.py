import base64
import smtplib
from email.message import EmailMessage
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.config import settings
from app.models.contact_message import ContactMessage


def _require_config(value: str, key: str) -> str:
    if not value:
        raise RuntimeError(f"Missing required notification setting: {key}")
    return value


def _normalize_whatsapp_number(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        raise RuntimeError("Missing WhatsApp destination number")
    if raw.startswith("whatsapp:"):
        return raw
    cleaned = raw.replace(" ", "").replace("-", "")
    if not cleaned.startswith("+"):
        raise RuntimeError("WhatsApp number must include country code, e.g. +917416106610")
    return f"whatsapp:{cleaned}"


def _message_body(message: ContactMessage) -> str:
    created_at = message.created_at.isoformat() if message.created_at else ""
    return (
        f"New contact form message (Ref #{message.id})\n\n"
        f"Parent Name: {message.parent_name}\n"
        f"Email: {message.email}\n"
        f"Country: {message.country}\n"
        f"Preferred Window: {message.preferred_contact_window}\n"
        f"Source Page: {message.source_page}\n"
        f"Created At (UTC): {created_at}\n\n"
        f"Message:\n{message.message}"
    )


def send_email_contact_alert(message: ContactMessage) -> None:
    smtp_host = _require_config(settings.SMTP_HOST, "SMTP_HOST")
    smtp_from = _require_config(settings.SMTP_FROM_EMAIL, "SMTP_FROM_EMAIL")
    smtp_to = _require_config(settings.CONTACT_ALERT_EMAIL_TO, "CONTACT_ALERT_EMAIL_TO")

    email = EmailMessage()
    email["Subject"] = f"[AviAcademy] New Contact Message #{message.id}"
    email["From"] = smtp_from
    email["To"] = smtp_to
    email.set_content(_message_body(message))

    with smtplib.SMTP(smtp_host, settings.SMTP_PORT, timeout=20) as server:
        if settings.SMTP_USE_TLS:
            server.starttls()
        if settings.SMTP_USERNAME:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(email)


def send_whatsapp_contact_alert(message: ContactMessage) -> None:
    account_sid = _require_config(settings.TWILIO_ACCOUNT_SID, "TWILIO_ACCOUNT_SID")
    auth_token = _require_config(settings.TWILIO_AUTH_TOKEN, "TWILIO_AUTH_TOKEN")
    sender = _normalize_whatsapp_number(_require_config(settings.TWILIO_WHATSAPP_FROM, "TWILIO_WHATSAPP_FROM"))
    recipient = _normalize_whatsapp_number(settings.CONTACT_ALERT_WHATSAPP_TO)

    body = _message_body(message)
    payload = urlencode(
        {
            "From": sender,
            "To": recipient,
            "Body": body[:1500],
        }
    ).encode("utf-8")

    request = Request(
        url=f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
        data=payload,
        method="POST",
    )
    basic_token = base64.b64encode(f"{account_sid}:{auth_token}".encode("utf-8")).decode("ascii")
    request.add_header("Authorization", f"Basic {basic_token}")
    request.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urlopen(request, timeout=20) as response:
            status = getattr(response, "status", 200)
            if status >= 400:
                raise RuntimeError(f"Twilio WhatsApp API returned status {status}")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Twilio WhatsApp API error {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Twilio WhatsApp API unreachable: {exc.reason}") from exc


def send_contact_alerts(message: ContactMessage) -> None:
    if not settings.CONTACT_ALERTS_ENABLED:
        return

    errors: list[str] = []

    try:
        send_email_contact_alert(message)
    except Exception as exc:
        errors.append(f"email: {exc}")

    try:
        send_whatsapp_contact_alert(message)
    except Exception as exc:
        errors.append(f"whatsapp: {exc}")

    if errors:
        raise RuntimeError("; ".join(errors))
