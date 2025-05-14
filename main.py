import logging
import pandas as pd
import os
from typing import Optional # For Python < 3.10 compatibility

from config import (
    LOG_FILE, LOG_LEVEL, JOB_DESCRIPTION_CSV, RESUMES_DIR, OLLAMA_LLM_MODEL, OLLAMA_EMBEDDING_MODEL
)
from utils.ollama_client import OllamaClient
from utils.db_manager import DBManager
from setup_db import create_tables

from agents.jd_summarizer_agent import JDSummarizerAgent
from agents.resume_matcher_agent import ResumeMatcherAgent
from agents.shortlister_agent import ShortlisterAgent
from agents.interview_scheduler_agent import InterviewSchedulerAgent


# --- Logging Setup ---
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


EXPECTED_JD_TEXT_COLUMN = "Job Description"  # <--- Your column name for JD text
EXPECTED_JD_TITLE_COLUMN = "Job Title"      # <--- Your column name for JD title (optional)
# --- Fallback column names if the above are not found (used by dummy data) ---
FALLBACK_JD_TEXT_COLUMN = "job_description_text"
FALLBACK_JD_TITLE_COLUMN = "job_title"


def run_pipeline():
    logger.info("🚀 Starting Recruitment Automation Pipeline 🚀")

    logger.info("Performing initial setup...")
    create_tables()
    logger.info("Database schema verified/created.")

    db_manager: Optional[DBManager] = None
    ollama_client: Optional[OllamaClient] = None

    try:
        ollama_client = OllamaClient()
        logger.info(f"Ollama client initialized. LLM: {OLLAMA_LLM_MODEL}, Embeddings: {OLLAMA_EMBEDDING_MODEL}")
    except ConnectionError as e:
        logger.error(f"CRITICAL: Could not connect to Ollama. Pipeline cannot proceed. {e}")
        # db_manager might not be initialized yet, so can't log to DB here easily.
        return

    try:
        db_manager = DBManager()
        logger.info("Database manager initialized.")

        jd_summarizer = JDSummarizerAgent(ollama_client, db_manager)
        resume_matcher = ResumeMatcherAgent(ollama_client, db_manager)
        shortlister = ShortlisterAgent(db_manager)
        scheduler = InterviewSchedulerAgent(db_manager)
        logger.info("All agents initialized.")

        logger.info(f"Loading job descriptions from: {JOB_DESCRIPTION_CSV}")
        jd_df: Optional[pd.DataFrame] = None # Ensure jd_df is defined for the scope

        # Determine which column names to primarily use
        jd_text_col_to_use = EXPECTED_JD_TEXT_COLUMN
        jd_title_col_to_use = EXPECTED_JD_TITLE_COLUMN

        if not os.path.exists(JOB_DESCRIPTION_CSV):
            logger.error(f"Job description CSV file not found: {JOB_DESCRIPTION_CSV}")
            db_manager.add_log("MainPipeline", "ERROR", f"JD CSV file not found: {JOB_DESCRIPTION_CSV}")
            logger.info(f"Creating a dummy {JOB_DESCRIPTION_CSV} for demonstration.")
            # Use fallback names for dummy data generation
            dummy_jd_data = {FALLBACK_JD_TITLE_COLUMN: ['Senior Python Developer'],
                             FALLBACK_JD_TEXT_COLUMN: ['We need a skilled Python developer with 5+ years experience in Django, Flask, and REST APIs. Must have a BS in Computer Science. Responsibilities include developing new features, maintaining existing code, and collaborating with the team. Strong problem-solving skills required.']}
            pd.DataFrame(dummy_jd_data).to_csv(JOB_DESCRIPTION_CSV, index=False, encoding='utf-8')
            logger.info(f"Dummy {JOB_DESCRIPTION_CSV} created. Please replace with your actual data.")
            # For dummy data, we know the column names
            jd_text_col_to_use = FALLBACK_JD_TEXT_COLUMN
            jd_title_col_to_use = FALLBACK_JD_TITLE_COLUMN
            jd_df = pd.read_csv(JOB_DESCRIPTION_CSV, encoding='utf-8')
        else:
            encodings_to_try = ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']
            for enc in encodings_to_try:
                try:
                    temp_df = pd.read_csv(JOB_DESCRIPTION_CSV, encoding=enc)
                    # Check if primary expected columns exist
                    if EXPECTED_JD_TEXT_COLUMN in temp_df.columns:
                        jd_text_col_to_use = EXPECTED_JD_TEXT_COLUMN
                        if EXPECTED_JD_TITLE_COLUMN in temp_df.columns:
                            jd_title_col_to_use = EXPECTED_JD_TITLE_COLUMN
                        else: # Use fallback for title if primary title not found
                            jd_title_col_to_use = FALLBACK_JD_TITLE_COLUMN 
                        jd_df = temp_df
                        logger.info(f"Successfully read {JOB_DESCRIPTION_CSV} with encoding: {enc} using columns: '{jd_text_col_to_use}', '{jd_title_col_to_use}' (optional)")
                        break
                    # Check if fallback text column exists (e.g., user named it like the dummy)
                    elif FALLBACK_JD_TEXT_COLUMN in temp_df.columns:
                        jd_text_col_to_use = FALLBACK_JD_TEXT_COLUMN
                        if FALLBACK_JD_TITLE_COLUMN in temp_df.columns:
                             jd_title_col_to_use = FALLBACK_JD_TITLE_COLUMN
                        else: # Use primary for title if fallback title not found but primary was defined
                             jd_title_col_to_use = EXPECTED_JD_TITLE_COLUMN
                        jd_df = temp_df
                        logger.info(f"Successfully read {JOB_DESCRIPTION_CSV} with encoding: {enc} using columns: '{jd_text_col_to_use}', '{jd_title_col_to_use}' (optional)")
                        break
                    else:
                        logger.warning(f"Neither '{EXPECTED_JD_TEXT_COLUMN}' nor '{FALLBACK_JD_TEXT_COLUMN}' found in {JOB_DESCRIPTION_CSV} with encoding {enc}. Trying next encoding or checking columns.")
                except UnicodeDecodeError:
                    logger.warning(f"Failed to read {JOB_DESCRIPTION_CSV} with encoding {enc}. Trying next...")
                except Exception as e_read:
                    logger.error(f"Error reading {JOB_DESCRIPTION_CSV} with encoding {enc}: {e_read}")

            if jd_df is None:
                logger.error(f"Failed to read {JOB_DESCRIPTION_CSV} with all attempted encodings or required columns not found.")
                db_manager.add_log("MainPipeline", "ERROR", f"Failed to read/parse JD CSV: {JOB_DESCRIPTION_CSV}")
                db_manager.close()
                return

        if jd_df.empty:
            logger.warning(f"Job description CSV ({JOB_DESCRIPTION_CSV}) is empty. No JDs to process.")
            db_manager.add_log("MainPipeline", "WARNING", "JD CSV is empty.")
            db_manager.close()
            return

        if jd_text_col_to_use not in jd_df.columns:
            logger.error(f"Job description text column ('{jd_text_col_to_use}') not found in {JOB_DESCRIPTION_CSV} after attempting to read.")
            db_manager.add_log("MainPipeline", "ERROR", f"Final check: '{jd_text_col_to_use}' column missing in JD CSV.")
            db_manager.close()
            return

        first_jd_series = jd_df.iloc[0]
        jd_raw_text = str(first_jd_series[jd_text_col_to_use])
        jd_title_from_csv = str(first_jd_series.get(jd_title_col_to_use, 'N/A Job Title')) # .get is safer for optional title

        logger.info(f"Processing Job Description: {jd_title_from_csv if jd_title_from_csv != 'N/A Job Title' else 'First JD in CSV'}")

        summarization_result = jd_summarizer.summarize_jd(jd_raw_text, source_file=f"{JOB_DESCRIPTION_CSV} (row 0)")

        if not summarization_result:
            logger.error(f"Failed to summarize the job description. Skipping further processing for this JD.")
            db_manager.add_log("MainPipeline", "ERROR", "JD summarization failed.")
            db_manager.close()
            return

        current_jd_id, jd_summary = summarization_result
        job_title_from_summary = jd_summary.get("job_title", jd_title_from_csv)
        logger.info(f"Job Description (ID: {current_jd_id}) summarized successfully: {job_title_from_summary}")

        logger.info(f"Starting resume processing from directory: {RESUMES_DIR}")
        if not os.path.exists(RESUMES_DIR) or not os.listdir(RESUMES_DIR):
            logger.warning(f"Resumes directory {RESUMES_DIR} is empty or does not exist. Creating dummy resumes if needed.")
            if not os.path.exists(RESUMES_DIR): os.makedirs(RESUMES_DIR)
            if not os.listdir(RESUMES_DIR):
                logger.info("Creating dummy resume files in data/CVs/ for demonstration.")
                try:
                    with open(os.path.join(RESUMES_DIR, "dummy_resume1.txt"), "w", encoding='utf-8') as f:
                        f.write("Alice Wonderland, alice@example.com. Python, Django, 3 years experience. BS in CS.")
                    with open(os.path.join(RESUMES_DIR, "dummy_resume2.txt"), "w", encoding='utf-8') as f:
                        f.write("Bob The Builder, bob@example.com. Java, Spring, 5 years experience. MS in Software Engineering.")
                    logger.warning("Created dummy .txt resumes. Please use PDF/DOCX for actual parsing.")
                except Exception as e_dummy_resume:
                    logger.error(f"Failed to create dummy resume files: {e_dummy_resume}")

        resume_matcher.process_resumes_for_jd(current_jd_id, jd_summary)
        logger.info(f"Resume matching completed for JD ID: {current_jd_id}")

        logger.info(f"Starting shortlisting for JD ID: {current_jd_id}")
        shortlister.shortlist_candidates(current_jd_id)
        logger.info(f"Shortlisting completed for JD ID: {current_jd_id}")

        logger.info(f"Starting interview scheduling for JD ID: {current_jd_id}")
        scheduler.schedule_interviews(current_jd_id, job_title=job_title_from_summary)
        logger.info(f"Interview scheduling process completed for JD ID: {current_jd_id}")

        logger.info("Displaying final candidate statuses for JD ID: %s", current_jd_id)
        final_candidates = db_manager.get_all_candidates_for_jd(current_jd_id)
        if final_candidates:
            logger.info(f"{'='*20} Final Candidate Statuses for JD ID: {current_jd_id} ({job_title_from_summary}) {'='*20}")
            for cand_data in final_candidates:
                cand_id, cand_name, cand_email, cand_score, cand_status, _, _ = cand_data[:7]
                logger.info(f"  - Name: {cand_name}, Email: {cand_email}, Score: {cand_score:.4f if cand_score is not None else 'N/A'}, Status: {cand_status}")
            logger.info(f"{'='*70}")
        else:
            logger.info("No candidates processed or found for this JD.")

    except Exception as e:
        logger.error(f"An unexpected error occurred in the main pipeline: {e}", exc_info=True)
        if db_manager: db_manager.add_log("MainPipeline", "CRITICAL", f"Pipeline failed: {e}")
    finally:
        if db_manager:
            db_manager.close()
            logger.info("Database connection closed.")
        logger.info("🏁 Recruitment Automation Pipeline Finished 🏁")

if __name__ == "__main__":
    run_pipeline()