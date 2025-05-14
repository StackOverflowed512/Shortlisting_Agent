import sqlite3
import logging
from config import DB_PATH

logger = logging.getLogger(__name__)

def create_tables():
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Job Descriptions Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_descriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_file TEXT, -- e.g., path to the CSV row or original JD file
            raw_text TEXT NOT NULL,
            summary_json TEXT, -- JSON string of skills, experience, etc.
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        logger.info("Table 'job_descriptions' checked/created successfully.")

        # Candidates Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_description_id INTEGER,
            candidate_name TEXT,
            email TEXT,
            phone TEXT,
            resume_file_path TEXT NOT NULL,
            extracted_resume_json TEXT, -- JSON string of extracted info
            match_score REAL,
            status TEXT CHECK(status IN ('parsed', 'summarized', 'matched', 'shortlisted', 'invited', 'rejected', 'error')), -- extended statuses
            interview_datetime TIMESTAMP,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            FOREIGN KEY (job_description_id) REFERENCES job_descriptions (id),
            UNIQUE (job_description_id, email) -- A candidate is unique per job posting by email
        )
        """)
        logger.info("Table 'candidates' checked/created successfully.")

        # Logs Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            agent_name TEXT,
            level TEXT CHECK(level IN ('INFO', 'DEBUG', 'WARNING', 'ERROR', 'CRITICAL')),
            message TEXT
        )
        """)
        logger.info("Table 'logs' checked/created successfully.")

        conn.commit()
        logger.info(f"Database schema setup/verified in {DB_PATH}")

    except sqlite3.Error as e:
        logger.error(f"Error creating tables in {DB_PATH}: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    create_tables()