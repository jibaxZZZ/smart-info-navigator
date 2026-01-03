"""Integration tools for external services - Pure business logic, NO AI.

Supported integrations (MVP):
- Email notifications via Gmail SMTP
"""

from typing import Dict, Any

from ..services.email_service import send_email, send_task_notification
from ..utils.logging import get_logger

logger = get_logger(__name__)


async def trigger_integration_tool(arguments: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Trigger external integration - Email only for MVP.

    Args:
        arguments: Tool arguments containing integration type and data
        user_id: Authenticated user ID

    Returns:
        MCP tool response with integration result

    Supported integrations:
        - email: Send email via Gmail SMTP

    Example:
        ```python
        # Send custom email
        result = await trigger_integration_tool({
            "integration_type": "email",
            "action": "send",
            "data": {
                "to": "user@example.com",
                "subject": "Task Update",
                "body": "Your task has been completed."
            }
        }, user_id="user-uuid")

        # Send task notification
        result = await trigger_integration_tool({
            "integration_type": "email",
            "action": "task_notification",
            "data": {
                "to": "user@example.com",
                "task_title": "Complete Q2 deliverables",
                "task_status": "completed",
                "task_id": "task-uuid"
            }
        }, user_id="user-uuid")
        ```
    """
    try:
        integration_type = arguments.get("integration_type")
        action = arguments.get("action", "send")
        data = arguments.get("data", {})

        logger.info(
            f"Triggering integration: {integration_type}/{action}",
            extra={
                "extra_fields": {
                    "integration_type": integration_type,
                    "action": action,
                    "user_id": user_id,
                }
            },
        )

        if integration_type == "email":
            # Handle email integration
            if action == "send":
                # Send custom email
                result = await send_email(
                    to=data.get("to"),
                    subject=data.get("subject"),
                    body=data.get("body"),
                    html=data.get("html"),
                    cc=data.get("cc"),
                    bcc=data.get("bcc"),
                )

                if result["success"]:
                    logger.info(f"Email sent successfully via integration")
                    return {
                        "success": True,
                        "data": result["details"],
                        "message": f"✅ {result['message']}",
                    }
                else:
                    logger.error(f"Email send failed: {result['error']}")
                    return {
                        "success": False,
                        "error": result["error"],
                    }

            elif action == "task_notification":
                # Send task notification
                result = await send_task_notification(
                    to=data.get("to"),
                    task_title=data.get("task_title"),
                    task_status=data.get("task_status"),
                    task_id=data.get("task_id"),
                )

                if result["success"]:
                    logger.info(f"Task notification sent successfully")
                    return {
                        "success": True,
                        "data": result["details"],
                        "message": f"✅ Task notification sent to {data.get('to')}",
                    }
                else:
                    logger.error(f"Task notification failed: {result['error']}")
                    return {
                        "success": False,
                        "error": result["error"],
                    }

            else:
                logger.error(f"Unknown email action: {action}")
                return {
                    "success": False,
                    "error": f"Unknown email action: {action}. Supported: 'send', 'task_notification'",
                }

        elif integration_type == "jira":
            # Jira integration deferred to Phase 2
            logger.warning("Jira integration not yet implemented")
            return {
                "success": False,
                "error": "Jira integration will be available in Phase 2",
            }

        elif integration_type == "slack":
            # Slack integration deferred to Phase 2
            logger.warning("Slack integration not yet implemented")
            return {
                "success": False,
                "error": "Slack integration will be available in Phase 2",
            }

        else:
            logger.error(f"Unknown integration type: {integration_type}")
            return {
                "success": False,
                "error": f"Unknown integration type: {integration_type}. Currently supported: 'email' (MVP). Coming soon: 'jira', 'slack'",
            }

    except Exception as e:
        logger.error(f"Error triggering integration: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to trigger integration: {str(e)}",
        }
