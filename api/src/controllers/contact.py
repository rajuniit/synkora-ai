"""
Contact form API controller.

Public endpoint for handling contact form submissions.
"""

import logging
import os
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_db
from src.services.integrations.email_service import EmailService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/contact", tags=["contact"])


class ContactFormRequest(BaseModel):
    """Contact form submission request."""

    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    subject: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=10, max_length=5000)


class ContactFormResponse(BaseModel):
    """Contact form submission response."""

    success: bool
    message: str


@router.post("", response_model=ContactFormResponse)
async def submit_contact_form(
    request: ContactFormRequest,
    db: AsyncSession = Depends(get_async_db),
) -> ContactFormResponse:
    """
    Submit a contact form message.

    This is a public endpoint - no authentication required.
    Sends an email to the support team with the contact form details.
    """
    try:
        email_service = EmailService(db)

        # Format the email content
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Contact Form Submission - Synkora</title>
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', sans-serif;
                    background-color: #f3f4f6;
                    color: #111827;
                    line-height: 1.6;
                }}
                .email-wrapper {{
                    width: 100%;
                    background-color: #f3f4f6;
                    padding: 40px 20px;
                }}
                .email-container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: #ffffff;
                    border-radius: 12px;
                    overflow: hidden;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
                }}
                .header {{
                    background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
                    padding: 30px 40px;
                    text-align: center;
                }}
                .logo {{
                    font-size: 24px;
                    font-weight: 700;
                    color: #ffffff;
                    margin: 0;
                }}
                .content {{
                    padding: 40px;
                }}
                .label {{
                    font-size: 12px;
                    font-weight: 600;
                    color: #6b7280;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    margin-bottom: 4px;
                }}
                .value {{
                    font-size: 16px;
                    color: #111827;
                    margin-bottom: 24px;
                    padding: 12px 16px;
                    background-color: #f9fafb;
                    border-radius: 8px;
                    border: 1px solid #e5e7eb;
                }}
                .message-box {{
                    font-size: 15px;
                    color: #374151;
                    margin-bottom: 24px;
                    padding: 16px;
                    background-color: #f9fafb;
                    border-radius: 8px;
                    border: 1px solid #e5e7eb;
                    white-space: pre-wrap;
                }}
                .footer {{
                    background-color: #f9fafb;
                    padding: 20px 40px;
                    border-top: 1px solid #e5e7eb;
                    text-align: center;
                }}
                .footer-text {{
                    font-size: 12px;
                    color: #6b7280;
                    margin: 0;
                }}
                .reply-btn {{
                    display: inline-block;
                    padding: 12px 24px;
                    background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
                    color: #ffffff;
                    text-decoration: none;
                    border-radius: 8px;
                    font-size: 14px;
                    font-weight: 600;
                    margin-top: 16px;
                }}
            </style>
        </head>
        <body>
            <div class="email-wrapper">
                <div class="email-container">
                    <div class="header">
                        <h1 class="logo">New Contact Form Submission</h1>
                    </div>
                    <div class="content">
                        <div class="label">From</div>
                        <div class="value">{request.name} &lt;{request.email}&gt;</div>

                        <div class="label">Subject</div>
                        <div class="value">{request.subject}</div>

                        <div class="label">Message</div>
                        <div class="message-box">{request.message}</div>

                        <div class="label">Submitted At</div>
                        <div class="value">{datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")} UTC</div>

                        <a href="mailto:{request.email}?subject=Re: {request.subject}" class="reply-btn">
                            Reply to {request.name}
                        </a>
                    </div>
                    <div class="footer">
                        <p class="footer-text">This message was sent via the Synkora contact form.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
New Contact Form Submission - Synkora

From: {request.name} <{request.email}>
Subject: {request.subject}

Message:
{request.message}

Submitted at: {datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")} UTC

---
This message was sent via the Synkora contact form.
        """

        # Send email to support
        result = await email_service.send_email(
            to_email=os.getenv("CONTACT_EMAIL", "hello@localhost"),
            subject=f"[Contact Form] {request.subject}",
            html_content=html_content,
            text_content=text_content,
            tenant_id=None,  # Platform-wide email config
        )

        if result.get("success"):
            logger.info(f"Contact form submitted successfully from {request.email}")
            return ContactFormResponse(
                success=True,
                message="Thank you for your message! We'll get back to you soon.",
            )
        else:
            logger.error(f"Failed to send contact form email: {result.get('message')}")
            # Still return success to user - we don't want to expose email config issues
            # In production, you might want to queue this for retry
            return ContactFormResponse(
                success=True,
                message="Thank you for your message! We'll get back to you soon.",
            )

    except Exception as e:
        logger.error(f"Error processing contact form: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to submit contact form. Please try again later.",
        )
