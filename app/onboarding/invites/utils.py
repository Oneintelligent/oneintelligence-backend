# app/onboarding/invites/utils.py
from app.onboarding.invites.models import InviteToken
from django.utils import timezone
from datetime import timedelta
from django.conf import settings

def create_invite(email: str, inviter_user_id=None, companyId=None, days_valid: int = 7) -> InviteToken:
    expires_at = timezone.now() + timedelta(days=days_valid)
    invite = InviteToken.objects.create(
        invited_user_email=email.strip().lower(),
        inviter_user_id=inviter_user_id,
        companyId=companyId,
        expires_at=expires_at
    )
    return invite

def send_invite_email(invite: InviteToken, invite_link_base: str = None):
    """
    Placeholder to send invite email.
    - invite_link_base should be your frontend route e.g. https://app.oneintelligence.com/invite
    - In production, replace with real email provider / templating.
    """
    if not invite_link_base:
        invite_link_base = getattr(settings, "INVITE_LINK_BASE", None)
    link = f"{invite_link_base.rstrip('/')}/{invite.token}" if invite_link_base else f"/invite/{invite.token}"
    # TODO: wire to your email system here (SendGrid, SES, etc.)
    subject = "You have been invited to join OneIntelligence"
    body = f"Hello,\n\nYou were invited to join the company workspace. Click to accept: {link}\n\nIf you did not request this, ignore."
    # Implement your send mail here. For now, just log or return link
    return {"link": link, "subject": subject, "body": body}
