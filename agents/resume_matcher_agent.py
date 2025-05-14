import os
import json
import logging
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from typing import Optional, Dict, List, Any, Union # Import necessary types

from utils.ollama_client import OllamaClient
from utils.db_manager import DBManager
from utils.file_parser import parse_resume
from config import RESUMES_DIR

logger = logging.getLogger(__name__)

class ResumeMatcherAgent:
    def __init__(self, ollama_client: OllamaClient, db_manager: DBManager):
        self.ollama_client = ollama_client
        self.db_manager = db_manager

    def _extract_structured_resume_data(self, resume_text: str, resume_filename: str) -> Optional[Dict[str, Any]]:
        prompt = f"""
        Analyze the following resume text and extract key information.
        Please format your response as a JSON object with the following keys:
        - "candidate_name": (string) Full name of the candidate. If not found, use "Unknown".
        - "email": (string) Email address. If not found, use "unknown@example.com".
        - "phone": (string, optional) Phone number.
        - "skills": (list of strings) Technical and soft skills.
        - "experience_summary": (string) A brief summary of total years of experience and key roles.
        - "education": (list of strings) Education details (e.g., "Bachelor's in CS - XYZ University").
        - "projects": (list of strings, optional) Key projects mentioned.

        Resume Text (first 4000 characters):
        ---
        {resume_text[:4000]}
        ---
        Ensure the output is a valid JSON object. If a field is not found, provide a sensible default (e.g., empty list for skills, "N/A" for text fields).
        Prioritize finding the candidate's name and email.
        """

        try:
            logger.info(f"Extracting structured data from resume: {resume_filename}")
            # llm_response type depends on ollama_client.generate_completion
            llm_response: Union[Dict[str, Any], str] = self.ollama_client.generate_completion(prompt, format_json=True)
            
            extracted_data: Optional[Dict[str, Any]] = None

            if isinstance(llm_response, str):
                try:
                    extracted_data = json.loads(llm_response)
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode LLM response into JSON for resume {resume_filename}. Response: {llm_response}")
                    self.db_manager.add_log("ResumeMatcherAgent", "ERROR", f"Failed to parse resume JSON: {resume_filename} - {llm_response[:200]}")
                    return None
            elif isinstance(llm_response, dict):
                extracted_data = llm_response
            else:
                logger.error(f"Unexpected data format from LLM for resume {resume_filename}. Type: {type(llm_response)}. Response: {str(llm_response)[:200]}")
                self.db_manager.add_log("ResumeMatcherAgent", "ERROR", f"Unexpected resume data format: {resume_filename} - {str(llm_response)[:200]}")
                return None
            
            if extracted_data is None: # Safeguard
                logger.error(f"extracted_data is None after LLM processing for resume {resume_filename}")
                return None

            # Basic validation and default values
            extracted_data.setdefault("candidate_name", "Unknown")
            # Ensure a somewhat unique placeholder email if extraction fails
            default_email_prefix = os.path.splitext(resume_filename)[0].replace(" ", "_").replace(".", "_")
            extracted_data.setdefault("email", f"unknown_{default_email_prefix}@example.com")
            extracted_data.setdefault("phone", None) # Explicitly None if not found
            extracted_data.setdefault("skills", [])
            extracted_data.setdefault("experience_summary", "N/A")
            extracted_data.setdefault("education", [])
            extracted_data.setdefault("projects", [])
            
            logger.info(f"Successfully extracted data for resume: {resume_filename}. Candidate: {extracted_data.get('candidate_name')}")
            return extracted_data

        except Exception as e:
            logger.error(f"Error extracting structured data from resume {resume_filename}: {e}", exc_info=True)
            self.db_manager.add_log("ResumeMatcherAgent", "ERROR", f"Exception during resume data extraction for {resume_filename}: {e}")
            return None

    def _calculate_similarity(self, text1_embedding: List[float], text2_embedding: List[float]) -> float:
        if not text1_embedding or not text2_embedding:
            logger.warning("One or both embeddings are empty, similarity cannot be calculated.")
            return 0.0
        
        if len(text1_embedding) == 0 or len(text2_embedding) == 0:
            logger.warning("One or both embeddings have zero length after conversion. Similarity cannot be calculated.")
            return 0.0
            
        emb1 = np.array(text1_embedding).reshape(1, -1)
        emb2 = np.array(text2_embedding).reshape(1, -1)
        
        if emb1.shape[1] != emb2.shape[1]:
            logger.error(f"Embedding dimensions mismatch: {emb1.shape[1]} vs {emb2.shape[1]}. Cannot calculate similarity.")
            return 0.0
        
        try:
            score = cosine_similarity(emb1, emb2)[0][0]
            return float(score) 
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0

    def process_resumes_for_jd(self, jd_id: int, jd_summary: Dict[str, Any]):
        logger.info(f"Starting resume processing for JD ID: {jd_id}")
        if not os.path.exists(RESUMES_DIR):
            logger.error(f"Resumes directory not found: {RESUMES_DIR}")
            self.db_manager.add_log("ResumeMatcherAgent", "ERROR", f"Resumes directory not found: {RESUMES_DIR}")
            return

        jd_skills = jd_summary.get("required_skills", [])
        jd_responsibilities = jd_summary.get("responsibilities", [])
        jd_experience = str(jd_summary.get("experience_years", "")) # Ensure string
        
        jd_text_for_embedding = f"Required Skills: {', '.join(jd_skills)}. Responsibilities: {', '.join(jd_responsibilities)}. Experience: {jd_experience}"
        if not jd_text_for_embedding.strip() or jd_text_for_embedding.strip() == "Required Skills: . Responsibilities: . Experience:":
            logger.error(f"JD ID {jd_id} has insufficient information in summary for embedding. Skills: {jd_skills}, Responsibilities: {jd_responsibilities}, Exp: {jd_experience}")
            self.db_manager.add_log("ResumeMatcherAgent", "ERROR", f"JD ID {jd_id} insufficient summary for embedding.")
            return

        logger.info(f"Generating embedding for JD ID: {jd_id} using text: '{jd_text_for_embedding[:100]}...'")
        jd_embedding: List[float] = self.ollama_client.generate_embedding(jd_text_for_embedding) # type: ignore # Ollama client returns list

        if not jd_embedding:
            logger.error(f"Failed to generate embedding for JD ID: {jd_id}. Skipping resume matching for this JD.")
            self.db_manager.add_log("ResumeMatcherAgent", "ERROR", f"Failed to generate embedding for JD ID: {jd_id}")
            return

        processed_count = 0
        for filename in os.listdir(RESUMES_DIR):
            resume_file_path = os.path.join(RESUMES_DIR, filename)
            if not (filename.lower().endswith(".pdf") or filename.lower().endswith(".docx")):
                logger.debug(f"Skipping non-resume file: {filename}")
                continue

            logger.info(f"Processing resume: {filename} for JD ID: {jd_id}")
            
            raw_resume_text = parse_resume(resume_file_path)
            if not raw_resume_text:
                logger.warning(f"Could not parse text from resume: {filename}. Skipping.")
                self.db_manager.add_log("ResumeMatcherAgent", "WARNING", f"Failed to parse resume: {filename}")
                self.db_manager.add_or_update_candidate(
                    job_description_id=jd_id,
                    candidate_name=f"ErrorParsing_{filename}",
                    email=f"error_parse_{os.path.splitext(filename)[0]}@system.local",
                    resume_file_path=resume_file_path,
                    status='error',
                    notes=f"Failed to parse resume text from {filename}"
                )
                continue

            structured_resume_data = self._extract_structured_resume_data(raw_resume_text, filename)
            if not structured_resume_data:
                logger.warning(f"Could not extract structured data from resume: {filename}. Skipping match.")
                self.db_manager.add_or_update_candidate(
                    job_description_id=jd_id,
                    candidate_name=f"ErrorExtracting_{filename}",
                    email=f"error_extract_{os.path.splitext(filename)[0]}@system.local",
                    resume_file_path=resume_file_path,
                    status='error',
                    notes=f"Failed to extract structured data from {filename}"
                )
                continue
            
            candidate_name = structured_resume_data.get("candidate_name", "Unknown")
            candidate_email = structured_resume_data.get("email", f"unknown_{os.path.splitext(filename)[0]}@example.com")
            candidate_phone = structured_resume_data.get("phone")

            candidate_id = self.db_manager.add_or_update_candidate(
                job_description_id=jd_id,
                candidate_name=candidate_name,
                email=candidate_email,
                phone=candidate_phone,
                resume_file_path=resume_file_path,
                extracted_resume_json=structured_resume_data,
                status='summarized'
            )
            if candidate_id is None:
                logger.error(f"Failed to add or update candidate {candidate_name} from {filename} in DB. Skipping matching.")
                continue # Skip if candidate couldn't be saved

            resume_skills = structured_resume_data.get("skills", [])
            resume_experience = str(structured_resume_data.get("experience_summary", "")) # Ensure string
            resume_text_for_embedding = f"Skills: {', '.join(resume_skills)}. Experience Summary: {resume_experience}"
            
            match_score = 0.0
            if not resume_text_for_embedding.strip() or resume_text_for_embedding.strip() == "Skills: . Experience Summary:":
                logger.warning(f"Resume {filename} has insufficient extracted data for embedding. Score will be 0.")
            else:
                logger.info(f"Generating embedding for resume: {filename} using text: '{resume_text_for_embedding[:100]}...'")
                resume_embedding: List[float] = self.ollama_client.generate_embedding(resume_text_for_embedding) # type: ignore
                if not resume_embedding:
                    logger.warning(f"Failed to generate embedding for resume: {filename}. Score will be 0.")
                else:
                    match_score = self._calculate_similarity(jd_embedding, resume_embedding)
            
            logger.info(f"Match score for {filename} (Candidate ID: {candidate_id}) with JD ID {jd_id}: {match_score:.4f}")
            
            self.db_manager.update_candidate_score_and_status(
                candidate_id=candidate_id,
                match_score=match_score,
                status='matched'
            )
            self.db_manager.add_log("ResumeMatcherAgent", "INFO", f"Processed resume {filename} for JD {jd_id}. Candidate ID: {candidate_id}, Score: {match_score:.4f}")
            processed_count += 1

        logger.info(f"Finished processing {processed_count} resumes for JD ID: {jd_id}.")