"""Support and Feedback API Route

Provides secure, rate-limited, anti-spam protected user feedback and support intake.
Does NOT leak secrets, documents, or server credentials in logs or payloads.
"""

import os
import json
import uuid
import time
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List
from collections import defaultdict
from threading import Lock

from fastapi import APIRouter, Request, HTTPException, status
from backend.config import config
from backend.api.schemas import ContactRequest, ContactResponse

logger = logging.getLogger("documind.support")
router = APIRouter(prefix="/support", tags=["support"])

# In-memory IP rate limiter: max 5 requests per 10 minutes per IP
_RATE_LIMIT_WINDOW_SECONDS = 600
_RATE_LIMIT_MAX_REQUESTS = 5
_ip_request_timestamps: Dict[str, List[float]] = defaultdict(list)
_rate_limit_lock = Lock()

def _check_rate_limit(client_ip: str) -> None:
    now = time.time()
    with _rate_limit_lock:
        window_start = now - _RATE_LIMIT_WINDOW_SECONDS
        timestamps = [ts for ts in _ip_request_timestamps[client_ip] if ts > window_start]
        if len(timestamps) >= _RATE_LIMIT_MAX_REQUESTS:
            oldest_in_window = timestamps[0]
            retry_after = int(oldest_in_window + _RATE_LIMIT_WINDOW_SECONDS - now) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Please wait {retry_after} seconds before submitting again.",
                headers={"Retry-After": str(max(1, retry_after))}
            )
        timestamps.append(now)
        _ip_request_timestamps[client_ip] = timestamps

def _mask_email(email: str) -> str:
    """Masks email address for privacy-safe logging (e.g. j***n@domain.com)."""
    try:
        user, domain = email.split("@", 1)
        if len(user) <= 2:
            masked_user = user[0] + "*"
        else:
            masked_user = user[0] + "*" * (len(user) - 2) + user[-1]
        return f"{masked_user}@{domain}"
    except Exception:
        return "***@***"

def _dispatch_support_notification(ref_id: str, payload: ContactRequest) -> None:
    """Delivers support message via configured SMTP or persists safely to data/support_messages.log."""
    log_file = config.data_dir / "support_messages.log"
    entry = {
        "reference_id": ref_id,
        "timestamp": time.time(),
        "category": payload.category,
        "name": payload.name,
        "email": payload.email,
        "subject": payload.subject,
        "message": payload.message,
    }
    
    # Always append to local support log
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        logger.error(f"Failed to record support message locally: {e}")

    # If SMTP is configured, attempt email delivery
    if config.smtp_host:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[DocuMind Support - {payload.category.upper()}] {payload.subject} (#{ref_id})"
            msg["From"] = config.smtp_sender
            msg["To"] = config.support_email_recipient
            msg["Reply-To"] = payload.email

            body = (
                f"Reference ID: {ref_id}\n"
                f"Category: {payload.category}\n"
                f"From: {payload.name} <{payload.email}>\n"
                f"Subject: {payload.subject}\n\n"
                f"Message:\n{payload.message}\n"
            )
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=10.0) as server:
                server.starttls()
                if config.smtp_user and config.smtp_password:
                    server.login(config.smtp_user, config.smtp_password)
                server.send_message(msg)
            logger.info(f"Support email dispatched successfully for ref #{ref_id}")
        except Exception as e:
            logger.warning(f"SMTP dispatch failed for #{ref_id} (recorded locally): {e}")

@router.post("/contact", response_model=ContactResponse)
def submit_contact_feedback(
    payload: ContactRequest,
    request: Request
):
    """Submits user support query, bug report, or product feedback.
    
    Includes rate limiting, honeypot spam protection, and sanitization.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    
    # 1. Enforce IP rate limiting
    _check_rate_limit(client_ip)

    # 2. Anti-spam honeypot verification
    # If the hidden honeypot field is filled, silently discard to fool bots
    if payload.website and payload.website.strip():
        fake_ref = uuid.uuid4().hex[:10]
        logger.info(f"Honeypot triggered from {client_ip}. Dropping spam submission silently.")
        return ContactResponse(
            status="received",
            message="Thank you for your feedback! Our engineering team has received your submission.",
            reference_id=fake_ref
        )

    # 3. Generate reference ID
    ref_id = f"DM-{uuid.uuid4().hex[:8].upper()}"

    # 4. Privacy-safe logging
    masked = _mask_email(payload.email)
    logger.info(f"Received support submission ref #{ref_id} [category={payload.category}] from {masked}")

    # 5. Dispatch message
    _dispatch_support_notification(ref_id, payload)

    return ContactResponse(
        status="received",
        message="Thank you for your feedback! Our engineering team has received your submission.",
        reference_id=ref_id
    )
