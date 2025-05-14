import logging
from datetime import datetime, timedelta
from utils.db_manager import DBManager
from utils.email_sender import send_email

logger = logging.getLogger(__name__)

class InterviewSchedulerAgent:
    def __init__(self, db_manager: DBManager):
        self.db_manager = db_manager

    def schedule_interviews(self, jd_id: int, job_title: str = "the Position"):
        logger.info(f"Starting interview scheduling for shortlisted candidates for JD ID: {jd_id} ({job_title})")
        
        shortlisted_candidates = self.db_manager.get_candidates_by_status_for_jd(jd_id, 'shortlisted')
        # get_candidates_by_status_for_jd returns: id, candidate_name, email, match_score, resume_file_path

        if not shortlisted_candidates:
            logger.info(f"No shortlisted candidates found for JD ID: {jd_id} to schedule interviews.")
            self.db_manager.add_log("InterviewSchedulerAgent", "INFO", f"No shortlisted candidates for JD {jd_id} to schedule.")
            return

        scheduled_count = 0
        for candidate_info in shortlisted_candidates:
            candidate_id, name, email, score, _ = candidate_info
            
            logger.info(f"Processing candidate {name} ({email}) for interview scheduling.")

            # Simple time slot suggestion (can be made more sophisticated)
            # For this example, let's suggest a generic time or ask them to reply
            # A real system might use a calendar API or a scheduling link.
            interview_time_suggestion = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d at 10:00 AM (Your Local Time)")
            
            subject = f"Interview Invitation: {job_title}"
            body = f"""
Dear {name},

Congratulations! We were impressed with your application for the {job_title} position (Ref JD ID: {jd_id}) and would like to invite you for an interview.

We have tentatively proposed an interview slot for you on:
{interview_time_suggestion}

Please reply to this email to confirm your availability or to request an alternative time.
We look forward to speaking with you.

Best regards,
The Hiring Team
"""
            # Send email
            email_sent = send_email(to_email=email, subject=subject, body=body)

            if email_sent:
                # Update candidate status and tentative interview time (or note that invitation was sent)
                # For simplicity, we'll just update status to 'invited'.
                # A real system might store the proposed slot or wait for confirmation.
                self.db_manager.update_candidate_status(candidate_id, 'invited') #, interview_datetime=interview_time_suggestion if you want to store it
                logger.info(f"Interview invitation sent to {name} ({email}). Status updated to 'invited'.")
                self.db_manager.add_log("InterviewSchedulerAgent", "INFO", f"Interview invitation sent to {name} (ID: {candidate_id}) for JD {jd_id}.")
                scheduled_count += 1
            else:
                logger.error(f"Failed to send interview invitation email to {name} ({email}).")
                self.db_manager.add_log("InterviewSchedulerAgent", "ERROR", f"Failed to send email to {name} (ID: {candidate_id}) for JD {jd_id}.")
                # Optionally, update status to 'invitation_failed' or retry later.

        logger.info(f"Interview scheduling process completed for JD ID: {jd_id}. Invitations sent to {scheduled_count} candidates.")