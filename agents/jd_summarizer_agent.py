import json
import logging
from utils.ollama_client import OllamaClient
from utils.db_manager import DBManager
from typing import Optional, Tuple, Dict, Any # Import necessary types

logger = logging.getLogger(__name__)

class JDSummarizerAgent:
    def __init__(self, ollama_client: OllamaClient, db_manager: DBManager):
        self.ollama_client = ollama_client
        self.db_manager = db_manager

    def summarize_jd(self, jd_text: str, source_file: str = "N/A") -> Optional[Tuple[int, Dict[str, Any]]]:
        prompt = f"""
        Analyze the following job description and extract key information.
        Please format your response as a JSON object with the following keys:
        - "job_title": (string) The job title.
        - "required_skills": (list of strings) Specific technical and soft skills mentioned.
        - "experience_years": (string or integer) Required years of experience (e.g., "3-5 years", 5).
        - "education_level": (string) Minimum education level required (e.g., "Bachelor's Degree in CS").
        - "responsibilities": (list of strings) Key responsibilities of the role.
        - "company_culture_keywords": (list of strings, optional) Keywords related to company culture if mentioned.
        - "location": (string, optional) Job location if specified.

        Job Description:
        ---
        {jd_text}
        ---

        Ensure the output is a valid JSON object.
        """
        try:
            logger.info(f"Summarizing Job Description from {source_file}...")
            # The ollama_client.generate_completion with format_json=True should return a dict
            # or a string that needs parsing if it failed.
            llm_response: Union[Dict[str, Any], str] = self.ollama_client.generate_completion(prompt, format_json=True)
            
            summary_data: Optional[Dict[str, Any]] = None

            if isinstance(llm_response, str):
                try:
                    summary_data = json.loads(llm_response)
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode LLM summary into JSON for JD from {source_file}. Response: {llm_response}")
                    self.db_manager.add_log("JDSummarizerAgent", "ERROR", f"Failed to parse JD summary JSON: {llm_response[:200]}")
                    return None
            elif isinstance(llm_response, dict):
                summary_data = llm_response
            else:
                logger.error(f"Unexpected summary format from LLM for JD from {source_file}. Type: {type(llm_response)}. Response: {str(llm_response)[:200]}")
                self.db_manager.add_log("JDSummarizerAgent", "ERROR", f"Unexpected JD summary format: {str(llm_response)[:200]}")
                return None

            if summary_data is None: # Should not happen if above logic is correct, but as a safeguard
                logger.error(f"summary_data is None after LLM processing for {source_file}")
                return None

            # Basic validation of expected keys (can be more robust)
            expected_keys = ["job_title", "required_skills", "experience_years", "education_level", "responsibilities"]
            # Initialize missing keys with default values
            summary_data.setdefault("job_title", "Not specified")
            summary_data.setdefault("required_skills", [])
            summary_data.setdefault("experience_years", "Not specified")
            summary_data.setdefault("education_level", "Not specified")
            summary_data.setdefault("responsibilities", [])
            summary_data.setdefault("company_culture_keywords", [])
            summary_data.setdefault("location", "Not specified")


            jd_id = self.db_manager.add_job_description(
                raw_text=jd_text,
                summary_json=summary_data,
                source_file=source_file
            )

            if jd_id is None:
                logger.error(f"Failed to store JD summary in database for {source_file}.")
                self.db_manager.add_log("JDSummarizerAgent", "ERROR", f"Failed to store JD summary for {source_file}")
                return None
                
            self.db_manager.add_log("JDSummarizerAgent", "INFO", f"Successfully summarized and stored JD (ID: {jd_id}) from {source_file}")
            logger.info(f"Successfully summarized JD from {source_file}. DB ID: {jd_id}")
            return jd_id, summary_data

        except Exception as e:
            logger.error(f"Error in JDSummarizerAgent for {source_file}: {e}", exc_info=True)
            self.db_manager.add_log("JDSummarizerAgent", "ERROR", f"Exception during JD summarization for {source_file}: {e}")
            return None