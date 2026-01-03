"""Email service using Gmail SMTP - Pure business logic, NO AI.

Provides email notification functionality via Gmail SMTP.
"""

import aiosmtplib
from email.message import EmailMessage
from typing import Optional, Dict, Any

from ..config import settings
from ..utils.logging import get_logger

logger = get_logger(__name__)


async def send_email(
    to: str,
    subject: str,
    body: str,
    html: Optional[str] = None,
    cc: Optional[list[str]] = None,
    bcc: Optional[list[str]] = None,
) -> Dict[str, Any]:
    """Send email via Gmail SMTP - pure business logic, NO AI.

    Args:
        to: Recipient email address
        subject: Email subject
        body: Plain text email body
        html: Optional HTML email body
        cc: Optional list of CC recipients
        bcc: Optional list of BCC recipients

    Returns:
        Dictionary with success status and details

    Example:
        ```python
        result = await send_email(
            to="user@example.com",
            subject="Task Completed",
            body="Your task 'Q2 Deliverables' has been completed."
        )
        ```
    """
    try:
        logger.info(
            f"Sending email to {to}",
            extra={"extra_fields": {"to": to, "subject": subject}},
        )

        # Validate SMTP configuration
        if not settings.smtp_user or not settings.smtp_password:
            logger.error("SMTP credentials not configured")
            return {
                "success": False,
                "error": "Email service not configured. Please set SMTP_USER and SMTP_PASSWORD.",
            }

        # Create email message
        message = EmailMessage()
        message["From"] = settings.smtp_from_email or settings.smtp_user
        message["To"] = to
        message["Subject"] = subject

        if cc:
            message["Cc"] = ", ".join(cc)
        if bcc:
            message["Bcc"] = ", ".join(bcc)

        # Set email body
        message.set_content(body)

        # Add HTML version if provided
        if html:
            message.add_alternative(html, subtype="html")

        # Send email
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            use_tls=settings.smtp_use_tls,
        )

        logger.info(
            f"Email sent successfully to {to}",
            extra={"extra_fields": {"to": to, "subject": subject}},
        )

        return {
            "success": True,
            "message": f"Email sent to {to}",
            "details": {
                "to": to,
                "subject": subject,
                "sent_at": None,  # Could add timestamp if needed
            },
        }

    except aiosmtplib.SMTPException as e:
        logger.error(f"SMTP error sending email: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to send email: SMTP error - {str(e)}",
        }
    except Exception as e:
        logger.error(f"Error sending email: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to send email: {str(e)}",
        }


async def send_task_notification(
    to: str, task_title: str, task_status: str, task_id: str
) -> Dict[str, Any]:
    """Send task notification email - pre-formatted template.

    Args:
        to: Recipient email address
        task_title: Title of the task
        task_status: Current status of the task
        task_id: Task ID

    Returns:
        Dictionary with success status
    """
    subject = f"Task Update: {task_title}"

    body = f"""
Hello,

Your task has been updated:

Task: {task_title}
Status: {task_status}
Task ID: {task_id}

---
Workflow Orchestrator
Automated notification - please do not reply to this email
"""

    html = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6;">
    <h2>Task Update Notification</h2>
    <p>Your task has been updated:</p>
    <table style="border-collapse: collapse; margin: 20px 0;">
        <tr>
            <td style="padding: 8px; font-weight: bold;">Task:</td>
            <td style="padding: 8px;">{task_title}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">Status:</td>
            <td style="padding: 8px;"><strong>{task_status}</strong></td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">Task ID:</td>
            <td style="padding: 8px;"><code>{task_id}</code></td>
        </tr>
    </table>
    <hr style="margin: 20px 0; border: none; border-top: 1px solid #ccc;">
    <p style="color: #666; font-size: 12px;">
        Workflow Orchestrator - Automated notification<br>
        Please do not reply to this email
    </p>
</body>
</html>
"""

    return await send_email(to=to, subject=subject, body=body, html=html)
