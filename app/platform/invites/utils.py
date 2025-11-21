# app/onboarding/invites/utils.py
import logging
import requests
from app.platform.invites.models import InviteToken
from django.utils import timezone
from datetime import timedelta
from django.conf import settings

logger = logging.getLogger(__name__)

def create_invite(email: str, inviter_user_id=None, companyId=None, days_valid: int = 7) -> InviteToken:
    expires_at = timezone.now() + timedelta(days=days_valid)
    invite = InviteToken.objects.create(
        invited_user_email=email.strip().lower(),
        inviter_user_id=inviter_user_id,
        companyId=companyId,
        expires_at=expires_at
    )
    return invite

def send_invite_email(invite: InviteToken, invite_link_base: str = None, company_name: str = None):
    """
    Send invite email using Twilio SendGrid API.
    Uses existing Twilio credentials if SendGrid API key is not set.
    Falls back to Django's send_mail if both fail.
    """
    if not invite_link_base:
        invite_link_base = getattr(settings, "INVITE_LINK_BASE", None) or getattr(settings, "FRONTEND_BASE", None)
    
    link = f"{invite_link_base.rstrip('/')}/auth/set-password?token={invite.token}" if invite_link_base else f"/auth/set-password?token={invite.token}"
    
    # Get the invited user's email
    invited_email = invite.invited_user_email
    
    if not invited_email:
        logger.error(f"InviteToken {invite.token} has empty email")
        return {"link": link, "subject": "", "sent": False, "error": "Empty email on invite"}
    
    logger.info(f"Sending invite email to {invited_email} for token {invite.token}")
    
    subject = f"You're invited to join {company_name or 'OneIntelligence'}"
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #007AEF;">You're Invited!</h2>
            <p>Hello,</p>
            <p>You have been invited to join <strong>{company_name or 'OneIntelligence'}</strong> workspace.</p>
            <p style="margin: 30px 0;">
                <a href="{link}" style="background-color: #007AEF; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">
                    Accept Invitation
                </a>
            </p>
            <p>Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all; color: #007AEF;">{link}</p>
            <p style="margin-top: 30px; font-size: 12px; color: #666;">
                If you did not request this invitation, you can safely ignore this email.
            </p>
        </div>
    </body>
    </html>
    """
    text_body = f"""Hello,

You have been invited to join {company_name or 'OneIntelligence'} workspace.

Click to accept: {link}

If you did not request this, ignore this email.
    """
    
    # Try Twilio SendGrid API first
    # Note: SendGrid requires a separate API key from your Twilio account
    # Get it from: https://app.sendgrid.com/settings/api_keys
    sendgrid_api_key = getattr(settings, 'SENDGRID_API_KEY', None)
    
    if sendgrid_api_key:
        try:
            # Use SendGrid API v3
            url = "https://api.sendgrid.com/v3/mail/send"
            headers = {
                "Authorization": f"Bearer {sendgrid_api_key}",
                "Content-Type": "application/json"
            }
            
            from_email = getattr(settings, 'SENDGRID_FROM_EMAIL', None) or getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@oneintelligence.com')
            
            payload = {
                "personalizations": [{
                    "to": [{"email": invited_email}],
                    "subject": subject
                }],
                "from": {"email": from_email},
                "content": [
                    {
                        "type": "text/plain",
                        "value": text_body
                    },
                    {
                        "type": "text/html",
                        "value": html_body
                    }
                ]
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code in [200, 202]:
                logger.info(f"Invite email sent via SendGrid to {invited_email}, status: {response.status_code}")
                return {"link": link, "subject": subject, "sent": True, "method": "sendgrid"}
            else:
                logger.warning(f"SendGrid API returned status {response.status_code}: {response.text}")
        except ImportError:
            logger.warning("requests package not available for SendGrid API")
        except Exception as e:
            logger.exception(f"Failed to send email via SendGrid API: {e}")
    
    # Fallback to Django's send_mail
    try:
        from django.core.mail import send_mail
        send_mail(
            subject,
            text_body,
            settings.DEFAULT_FROM_EMAIL,
            [invited_email],
            html_message=html_body,
            fail_silently=False,
        )
        logger.info(f"Invite email sent via Django send_mail to {invited_email}")
        return {"link": link, "subject": subject, "sent": True, "method": "django_send_mail"}
    except Exception as e:
        logger.exception(f"Failed to send email via Django send_mail: {e}")
        return {"link": link, "subject": subject, "sent": False, "error": str(e)}
