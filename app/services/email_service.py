"""
JobKit - Email Service

Supports two delivery methods:
    1. Resend HTTP API (recommended for cloud platforms like Render/Railway)
    2. SMTP fallback (for local dev or self-hosted with Gmail, SES, etc.)

Resend is checked first. If RESEND_API_KEY is not set, falls back to SMTP.
Gracefully degrades: if neither is configured, logs a warning and returns False.
"""
import logging
from typing import Optional

import httpx

from ..config import settings

logger = logging.getLogger("jobkit.email")


class EmailService:
    """Async email service with Resend HTTP API and SMTP fallback."""

    RESEND_API_URL = "https://api.resend.com/emails"

    def is_configured(self) -> bool:
        """Check if any email backend is configured."""
        return bool(
            settings.email.resend_api_key
            or (settings.email.smtp_host and settings.email.smtp_username)
        )

    def _use_resend(self) -> bool:
        """Check if Resend API key is set."""
        return bool(settings.email.resend_api_key)

    async def _send_via_resend(
        self, to_email: str, subject: str, html_body: str
    ) -> bool:
        """Send email via Resend HTTP API."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.RESEND_API_URL,
                    headers={
                        "Authorization": f"Bearer {settings.email.resend_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "from": f"{settings.email.from_name} <{settings.email.from_email}>",
                        "to": [to_email],
                        "subject": subject,
                        "html": html_body,
                    },
                    timeout=10.0,
                )

            if response.status_code == 200:
                logger.info("Email sent via Resend to %s: %s", to_email, subject)
                return True
            else:
                logger.error(
                    "Resend API error (%s): %s", response.status_code, response.text
                )
                return False
        except Exception as e:
            logger.error("Failed to send email via Resend to %s: %s", to_email, e)
            return False

    async def _send_via_smtp(
        self, to_email: str, subject: str, html_body: str, text_body: Optional[str] = None
    ) -> bool:
        """Send email via SMTP."""
        try:
            import aiosmtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            message = MIMEMultipart("alternative")
            message["From"] = f"{settings.email.from_name} <{settings.email.from_email}>"
            message["To"] = to_email
            message["Subject"] = subject

            if text_body:
                message.attach(MIMEText(text_body, "plain"))
            message.attach(MIMEText(html_body, "html"))

            await aiosmtplib.send(
                message,
                hostname=settings.email.smtp_host,
                port=settings.email.smtp_port,
                username=settings.email.smtp_username,
                password=settings.email.smtp_password,
                start_tls=settings.email.smtp_use_tls,
            )
            logger.info("Email sent via SMTP to %s: %s", to_email, subject)
            return True
        except Exception as e:
            logger.error("Failed to send email via SMTP to %s: %s", to_email, e)
            return False

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
    ) -> bool:
        """Send an email. Uses Resend if configured, otherwise SMTP."""
        if not self.is_configured():
            logger.warning("Email not configured — skipping send to %s", to_email)
            return False

        if self._use_resend():
            return await self._send_via_resend(to_email, subject, html_body)
        else:
            return await self._send_via_smtp(to_email, subject, html_body, text_body)

    async def send_verification_email(
        self, to_email: str, token: str, user_name: str = ""
    ) -> bool:
        """Send email verification link."""
        verify_url = f"{settings.base_url}/auth/verify-email?token={token}"
        greeting = f"Hi {user_name}," if user_name else "Hi,"

        html = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                     max-width: 480px; margin: 0 auto; padding: 24px;">
            <h2 style="color: #2563eb; margin-bottom: 16px;">Verify your JobKit account</h2>
            <p>{greeting}</p>
            <p>Please verify your email address by clicking the button below:</p>
            <p style="text-align: center; margin: 32px 0;">
                <a href="{verify_url}"
                   style="background: #2563eb; color: white; padding: 12px 24px;
                          border-radius: 8px; text-decoration: none; font-weight: 600;
                          display: inline-block;">
                    Verify Email
                </a>
            </p>
            <p style="color: #6b7280; font-size: 14px;">
                Or copy this link:<br>
                <a href="{verify_url}" style="color: #2563eb; word-break: break-all;">{verify_url}</a>
            </p>
            <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;">
            <p style="color: #9ca3af; font-size: 12px;">
                This link expires in 24 hours. If you didn't create a JobKit account, ignore this email.
            </p>
        </div>
        """
        return await self.send_email(to_email, "Verify your JobKit email", html)

    async def send_password_reset_email(
        self, to_email: str, token: str, user_name: str = ""
    ) -> bool:
        """Send password reset link."""
        reset_url = f"{settings.base_url}/reset-password?token={token}"
        greeting = f"Hi {user_name}," if user_name else "Hi,"

        html = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                     max-width: 480px; margin: 0 auto; padding: 24px;">
            <h2 style="color: #2563eb; margin-bottom: 16px;">Reset your password</h2>
            <p>{greeting}</p>
            <p>We received a request to reset your JobKit password. Click below to set a new one:</p>
            <p style="text-align: center; margin: 32px 0;">
                <a href="{reset_url}"
                   style="background: #2563eb; color: white; padding: 12px 24px;
                          border-radius: 8px; text-decoration: none; font-weight: 600;
                          display: inline-block;">
                    Reset Password
                </a>
            </p>
            <p style="color: #6b7280; font-size: 14px;">
                Or copy this link:<br>
                <a href="{reset_url}" style="color: #2563eb; word-break: break-all;">{reset_url}</a>
            </p>
            <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;">
            <p style="color: #9ca3af; font-size: 12px;">
                This link expires in 1 hour. If you didn't request a password reset, ignore this email.
            </p>
        </div>
        """
        return await self.send_email(to_email, "Reset your JobKit password", html)


# Global instance
email_service = EmailService()
