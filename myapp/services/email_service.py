import logging
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

logger = logging.getLogger(__name__)


def send_employee_invitation_email(employee, invitation, accept_url):
    """
    Sends official HTML & Plain Text invitation email via SMTP backend.
    """
    subject = f"Official Invitation: Join Nalanda District Infrastructure Portal (NDISP)"
    recipient_email = invitation.email
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@nalanda.gov.in')

    role_name = invitation.role.name if invitation.role else "Department Officer"
    dept_name = employee.department.name if employee.department else "Water Resources Department"

    plain_text = f"""
Dear {employee.full_name},

You have been invited to join the Nalanda District Infrastructure Portal (NDISP) as {role_name} in the {dept_name}.

Employee Code: {employee.employee_code}
Designation  : {employee.designation}
Office       : {employee.office}
Block        : {employee.block}

Please click the link below to accept your invitation, set your password, and activate your account:
{accept_url}

This invitation link will expire in 7 days.

Best regards,
Department Administration Team
Nalanda District Infrastructure Portal (NDISP)
    """.strip()

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; color: #0f172a; margin: 0; padding: 20px; }}
        .email-container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; }}
        .email-header {{ background: #0f2b48; color: #ffffff; padding: 24px; text-align: center; }}
        .email-body {{ padding: 32px 24px; line-height: 1.6; }}
        .badge {{ background: #e0f2fe; color: #0369a1; padding: 4px 10px; border-radius: 12px; font-weight: 600; font-size: 12px; }}
        .btn {{ display: inline-block; background-color: #0f2b48; color: #ffffff !important; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; margin-top: 20px; text-align: center; }}
        .footer {{ padding: 20px; background: #f1f5f9; font-size: 12px; color: #64748b; text-align: center; border-top: 1px solid #e2e8f0; }}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="email-header">
            <h2 style="margin:0;">NALANDA DISTRICT INFRASTRUCTURE PORTAL</h2>
            <p style="margin:5px 0 0 0; font-size: 13px; color: #93c5fd;">OFFICIAL WORKFORCE ONBOARDING INVITATION</p>
        </div>
        <div class="email-body">
            <h3>Dear {employee.full_name},</h3>
            <p>You have been invited by your Department Head to join the official government portal as a registered workforce member.</p>
            
            <table style="width:100%; border-collapse: collapse; margin: 20px 0; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px;">
                <tr><td style="padding:10px; font-weight:600; color:#475569;">Employee Code:</td><td style="padding:10px; font-family:monospace;">{employee.employee_code}</td></tr>
                <tr><td style="padding:10px; font-weight:600; color:#475569;">Designation:</td><td style="padding:10px;">{employee.designation}</td></tr>
                <tr><td style="padding:10px; font-weight:600; color:#475569;">Department:</td><td style="padding:10px;">{dept_name}</td></tr>
                <tr><td style="padding:10px; font-weight:600; color:#475569;">Assigned RBAC Role:</td><td style="padding:10px;"><span class="badge">{role_name}</span></td></tr>
                <tr><td style="padding:10px; font-weight:600; color:#475569;">Office / Block:</td><td style="padding:10px;">{employee.office} ({employee.block})</td></tr>
            </table>

            <p style="text-align: center;">
                <a href="{accept_url}" class="btn">Accept Invitation & Activate Account</a>
            </p>

            <p style="font-size: 12px; color: #64748b; margin-top: 25px;">If the button above does not work, copy and paste the following link into your browser:<br><a href="{accept_url}">{accept_url}</a></p>
        </div>
        <div class="footer">
            This is an official automated invitation from the Nalanda District Infrastructure Portal (NDISP). Please do not reply to this email.
        </div>
    </div>
</body>
</html>
    """.strip()

    try:
        msg = EmailMultiAlternatives(subject, plain_text, from_email, [recipient_email])
        msg.attach_alternative(html_content, "text/html")
        sent = msg.send(fail_silently=False)
        if sent:
            logger.info(f"SMTP Invitation email sent successfully to {recipient_email}")
            return True, "Email sent via SMTP"
        else:
            logger.warning(f"SMTP Email send returned 0 for {recipient_email}.")
            return False, "SMTP Backend returned 0"
    except Exception as e:
        logger.error(f"Failed to send SMTP email to {recipient_email}: {str(e)}")
        return False, str(e)


def send_password_reset_otp_email(user, otp_code):
    """
    Sends 6-digit Password Reset OTP email via HTML & Plain Text email.
    """
    subject = "Password Reset OTP - Nalanda District Infrastructure Portal (NDISP)"
    recipient_email = user.email
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@nalanda.gov.in')
    user_name = user.get_full_name() or user.username

    plain_text = f"""
Dear {user_name},

You have requested to reset your password on the Nalanda District Infrastructure Portal (NDISP).

Your Password Reset OTP is: {otp_code}

This OTP is valid for 10 minutes. Please do not share this OTP with anyone for security reasons.

If you did not request a password reset, please ignore this email.

Best regards,
System Security Team
Nalanda District Infrastructure Portal (NDISP)
    """.strip()

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; color: #0f172a; margin: 0; padding: 20px; }}
        .email-container {{ max-width: 550px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; }}
        .email-header {{ background: #0f2b48; color: #ffffff; padding: 20px; text-align: center; }}
        .email-body {{ padding: 28px 24px; line-height: 1.6; text-align: center; }}
        .otp-box {{ display: inline-block; background: #f0f9ff; color: #0369a1; border: 2px dashed #0284c7; padding: 14px 28px; border-radius: 10px; font-size: 32px; font-weight: 800; letter-spacing: 6px; margin: 20px 0; }}
        .footer {{ padding: 16px; background: #f1f5f9; font-size: 12px; color: #64748b; text-align: center; border-top: 1px solid #e2e8f0; }}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="email-header">
            <h2 style="margin:0; font-size: 20px;">NALANDA DISTRICT INFRASTRUCTURE PORTAL</h2>
            <p style="margin:4px 0 0 0; font-size: 12px; color: #93c5fd;">PASSWORD RESET VERIFICATION</p>
        </div>
        <div class="email-body">
            <h3 style="text-align: left; margin-top:0;">Hello {user_name},</h3>
            <p style="text-align: left;">We received a request to reset your password. Use the Verification Code (OTP) below to proceed:</p>
            
            <div class="otp-box">{otp_code}</div>

            <p style="font-size: 13px; color: #64748b;">⏱️ This OTP is valid for <strong>10 minutes</strong>. Do not share it with anyone.</p>
            <p style="font-size: 12px; color: #94a3b8; text-align: left; margin-top: 20px;">If you didn't request a password reset, you can safely ignore this email.</p>
        </div>
        <div class="footer">
            Official Security Notification from NDISP. Please do not reply to this automated email.
        </div>
    </div>
</body>
</html>
    """.strip()

    try:
        msg = EmailMultiAlternatives(subject, plain_text, from_email, [recipient_email])
        msg.attach_alternative(html_content, "text/html")
        sent = msg.send(fail_silently=False)
        if sent:
            logger.info(f"Password reset OTP email sent to {recipient_email}")
            return True, "OTP Email sent via SMTP"
        else:
            logger.warning(f"SMTP send returned 0 for {recipient_email}")
            return False, "SMTP Backend returned 0"
    except Exception as e:
        logger.error(f"Failed to send OTP email to {recipient_email}: {str(e)}")
        return False, str(e)

