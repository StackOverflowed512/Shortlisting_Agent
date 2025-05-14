import logging
from utils.db_manager import DBManager
from config import SHORTLIST_THRESHOLD

logger = logging.getLogger(__name__)

class ShortlisterAgent:
    def __init__(self, db_manager: DBManager):
        self.db_manager = db_manager

    def shortlist_candidates(self, jd_id: int):
        logger.info(f"Starting shortlisting process for JD ID: {jd_id} with threshold >= {SHORTLIST_THRESHOLD}")
        
        # Get all candidates with status 'matched' for the given JD
        # The schema for get_all_candidates_for_jd returns:
        # id, candidate_name, email, match_score, status, resume_file_path, extracted_resume_json
        candidates_to_evaluate = self.db_manager.get_all_candidates_for_jd(jd_id)

        shortlisted_count = 0
        if not candidates_to_evaluate:
            logger.info(f"No candidates found with 'matched' status for JD ID: {jd_id} to shortlist.")
            return

        for candidate_data in candidates_to_evaluate:
            candidate_id = candidate_data[0]
            candidate_name = candidate_data[1]
            match_score = candidate_data[3]
            current_status = candidate_data[4]

            if current_status != 'matched': # Only process 'matched' candidates
                logger.debug(f"Skipping candidate {candidate_name} (ID: {candidate_id}) with status {current_status}")
                continue
            
            if match_score is None:
                logger.warning(f"Candidate {candidate_name} (ID: {candidate_id}) has no match score. Skipping.")
                continue

            if match_score >= SHORTLIST_THRESHOLD:
                self.db_manager.update_candidate_status(candidate_id, 'shortlisted')
                logger.info(f"Candidate {candidate_name} (ID: {candidate_id}) shortlisted with score {match_score:.4f} for JD ID: {jd_id}")
                self.db_manager.add_log("ShortlisterAgent", "INFO", f"Candidate ID {candidate_id} ({candidate_name}) shortlisted for JD {jd_id}. Score: {match_score:.4f}")
                shortlisted_count += 1
            else:
                # Optionally, mark as 'rejected' or keep as 'matched' if no explicit rejection step
                # self.db_manager.update_candidate_status(candidate_id, 'rejected_auto_score')
                logger.info(f"Candidate {candidate_name} (ID: {candidate_id}) not shortlisted. Score: {match_score:.4f} (below threshold {SHORTLIST_THRESHOLD})")


        logger.info(f"Shortlisting complete for JD ID: {jd_id}. {shortlisted_count} candidates shortlisted.")
        self.db_manager.add_log("ShortlisterAgent", "INFO", f"Shortlisting complete for JD {jd_id}. {shortlisted_count} candidates met threshold.")