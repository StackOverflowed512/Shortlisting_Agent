import smtplib
from email.mime.text import MIMEText
import logging
from config import SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SENDER_EMAIL, ENABLE_EMAIL_SENDING

logger = logging.getLogger(__name__)

def send_email(to_email: str, subject: str, body: str) -> bool:
    if not ENABLE_EMAIL_SENDING:
        logger.info(f"Email sending is disabled. Would send to: {to_email}")
        print("--- MOCK EMAIL ---")
        print(f"To: {to_email}")
        print(f"From: {SENDER_EMAIL}")
        print(f"Subject: {subject}")
        print(f"Body:\n{body}")
        print("--- END MOCK EMAIL ---")
        return True # Simulate success

    if not all([SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SENDER_EMAIL]):
        logger.error("SMTP configuration is incomplete. Cannot send email.")
        return False

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = to_email

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Secure the connection
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        logger.info(f"Email sent successfully to {to_email} with subject: {subject}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP Authentication Error: {e}. Check username/password and mail server settings (e.g., 'less secure app access' for Gmail).")
        return False
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    # Test email sending (ensure .env is configured if ENABLE_EMAIL_SENDING is True)
    # Replace with a test recipient you control
    test_recipient = "test_recipient@example.com" 
    if ENABLE_EMAIL_SENDING and SMTP_USERNAME != "your_email@example.com": # A crude check if config might be real
        print(f"Attempting to send a real email to {test_recipient}. Check your .env file.")
        success = send_email(
            to_email=test_recipient,
            subject="Test Email from Recruitment System",
            body="This is a test email.\n\nIf you received this, the email sending functionality is working."
        )
        if success:
            print(f"Test email ostensibly sent to {test_recipient}. Check inbox/spam.")
        else:
            print(f"Test email failed to send to {test_recipient}.")
    else:
        print("Email sending is disabled or using default placeholder config. Simulating email send.")
        send_email(
            to_email=test_recipient,
            subject="Test Email from Recruitment System (Mock)",
            body="This is a test email (mock).\n\nIf you see this in console, the mock email functionality is working."
        )