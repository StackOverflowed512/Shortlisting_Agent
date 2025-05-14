import sqlite3
import json
import logging
from datetime import datetime
from config import DB_PATH
from typing import Optional, Union, List, Any # Import necessary types

logger = logging.getLogger(__name__)

class DBManager:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None
        self._connect()

    def _connect(self):
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            logger.info(f"Successfully connected to database: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Error connecting to database {self.db_path}: {e}")
            raise

    def close(self):
        if self.conn:
            self.conn.close()
            logger.info(f"Database connection closed: {self.db_path}")

    def execute_query(self, query: str, params: Optional[tuple] = None) -> Optional[sqlite3.Cursor]:
        if not self.conn or not self.cursor:
            logger.error("Database not connected. Cannot execute query.")
            # Or raise an exception
            return None
        try:
            self.cursor.execute(query, params or ())
            self.conn.commit()
            return self.cursor
        except sqlite3.Error as e:
            logger.error(f"Error executing query: {query} with params {params}. Error: {e}")
            # self.conn.rollback()
            raise
        return None # Should not be reached if exception is raised

    def fetch_one(self, query: str, params: Optional[tuple] = None) -> Optional[tuple]:
        if not self.conn or not self.cursor:
            logger.error("Database not connected. Cannot fetch one.")
            return None
        try:
            self.cursor.execute(query, params or ())
            return self.cursor.fetchone()
        except sqlite3.Error as e:
            logger.error(f"Error fetching one: {query} with params {params}. Error: {e}")
            raise
        return None # Should not be reached

    def fetch_all(self, query: str, params: Optional[tuple] = None) -> List[tuple]:
        if not self.conn or not self.cursor:
            logger.error("Database not connected. Cannot fetch all.")
            return []
        try:
            self.cursor.execute(query, params or ())
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Error fetching all: {query} with params {params}. Error: {e}")
            raise
        return [] # Should not be reached

    # --- Job Description Methods ---
    def add_job_description(self, raw_text: str, summary_json: dict, source_file: Optional[str] = None) -> Optional[int]:
        query = """
        INSERT INTO job_descriptions (raw_text, summary_json, source_file, created_at)
        VALUES (?, ?, ?, ?)
        """
        params = (raw_text, json.dumps(summary_json), source_file, datetime.now().isoformat())
        cursor = self.execute_query(query, params)
        if cursor:
            logger.info(f"Added job description from {source_file or 'raw text'} with ID: {cursor.lastrowid}")
            return cursor.lastrowid
        return None

    def get_job_description_by_id(self, jd_id: int) -> Optional[tuple]: # Changed here
        query = "SELECT id, raw_text, summary_json, source_file, created_at FROM job_descriptions WHERE id = ?"
        row = self.fetch_one(query, (jd_id,))
        if row:
            try:
                # Unpack and potentially transform elements
                # summary_json is at index 2
                parsed_summary = json.loads(row[2]) if row[2] else {}
                return (row[0], row[1], parsed_summary, row[3], row[4])
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse summary_json for JD ID {jd_id}: {e}")
                # Return row with raw JSON string or handle error as appropriate
                return (row[0], row[1], row[2], row[3], row[4]) # Or None
        return None

    # --- Candidate Methods ---
    def add_or_update_candidate(self, job_description_id: int, candidate_name: str, email: str,
                                resume_file_path: str, extracted_resume_json: Optional[dict] = None,
                                match_score: Optional[float] = None, status: str = 'parsed',
                                phone: Optional[str] = None, notes: Optional[str] = None) -> Optional[int]:
        now = datetime.now().isoformat()

        existing_candidate = self.fetch_one(
            "SELECT id FROM candidates WHERE email = ? AND job_description_id = ?",
            (email, job_description_id)
        )

        candidate_id: Optional[int] = None

        if existing_candidate:
            candidate_id = existing_candidate[0]
            query = """
            UPDATE candidates
            SET candidate_name = ?, resume_file_path = ?, extracted_resume_json = ?,
                match_score = COALESCE(?, match_score), status = COALESCE(?, status),
                phone = COALESCE(?, phone), notes = COALESCE(?, notes), updated_at = ?
            WHERE id = ?
            """
            params = (candidate_name, resume_file_path,
                      json.dumps(extracted_resume_json) if extracted_resume_json else None,
                      match_score, status, phone, notes, now, candidate_id)
            self.execute_query(query, params)
            logger.info(f"Updated candidate {candidate_name} ({email}) with ID: {candidate_id} for JD {job_description_id}")
        else:
            query = """
            INSERT INTO candidates (job_description_id, candidate_name, email, phone, resume_file_path,
                                   extracted_resume_json, match_score, status, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (job_description_id, candidate_name, email, phone, resume_file_path,
                      json.dumps(extracted_resume_json) if extracted_resume_json else None,
                      match_score, status, notes, now, now)
            cursor = self.execute_query(query, params)
            if cursor:
                candidate_id = cursor.lastrowid
                logger.info(f"Added candidate {candidate_name} ({email}) with ID: {candidate_id} for JD {job_description_id}")
        return candidate_id


    def get_candidate_by_email_and_jd(self, email: str, job_description_id: int) -> Optional[tuple]: # Changed here
        query = """
        SELECT id, job_description_id, candidate_name, email, phone, resume_file_path,
               extracted_resume_json, match_score, status, interview_datetime, notes, created_at, updated_at
        FROM candidates
        WHERE email = ? AND job_description_id = ?
        """
        row = self.fetch_one(query, (email, job_description_id))
        if row:
            try:
                # extracted_resume_json is at index 6
                parsed_resume_json = json.loads(row[6]) if row[6] else None
                return (*row[:6], parsed_resume_json, *row[7:])
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse extracted_resume_json for candidate email {email}, JD ID {job_description_id}: {e}")
                return (*row[:6], row[6], *row[7:]) # Or None
        return None

    def update_candidate_score_and_status(self, candidate_id: int, match_score: float, status: str):
        query = "UPDATE candidates SET match_score = ?, status = ?, updated_at = ? WHERE id = ?"
        params = (match_score, status, datetime.now().isoformat(), candidate_id)
        self.execute_query(query, params)
        logger.info(f"Updated candidate ID {candidate_id} score to {match_score}, status to {status}")

    def update_candidate_status(self, candidate_id: int, status: str, interview_datetime: Optional[str] = None):
        query = "UPDATE candidates SET status = ?, updated_at = ?"
        params_list: List[Any] = [status, datetime.now().isoformat()]

        if interview_datetime:
            query += ", interview_datetime = ?"
            params_list.append(interview_datetime)

        query += " WHERE id = ?"
        params_list.append(candidate_id)

        self.execute_query(query, tuple(params_list))
        logger.info(f"Updated candidate ID {candidate_id} status to {status}" + (f" and interview time to {interview_datetime}" if interview_datetime else ""))

    def get_candidates_by_status_for_jd(self, job_description_id: int, status: str) -> List[tuple]:
        query = """
        SELECT id, candidate_name, email, match_score, resume_file_path
        FROM candidates
        WHERE job_description_id = ? AND status = ?
        """
        return self.fetch_all(query, (job_description_id, status))

    def get_all_candidates_for_jd(self, job_description_id: int) -> List[tuple]:
        query = """
        SELECT id, candidate_name, email, match_score, status, resume_file_path, extracted_resume_json
        FROM candidates
        WHERE job_description_id = ?
        ORDER BY match_score DESC
        """
        rows = self.fetch_all(query, (job_description_id,))
        processed_rows = []
        for row in rows:
            try:
                # extracted_resume_json is at index 6
                parsed_resume_json = json.loads(row[6]) if row[6] else None
                processed_rows.append((*row[:6], parsed_resume_json, *row[7:])) # row[7:] would be empty here based on SELECT
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse extracted_resume_json for candidate ID {row[0]} in get_all_candidates_for_jd: {e}")
                processed_rows.append((*row[:6], row[6], *row[7:])) # Return with raw JSON
        return processed_rows


    # --- Log Methods ---
    def add_log(self, agent_name: str, level: str, message: str):
        query = "INSERT INTO logs (timestamp, agent_name, level, message) VALUES (?, ?, ?, ?)"
        params = (datetime.now().isoformat(), agent_name, level, message)
        self.execute_query(query, params)