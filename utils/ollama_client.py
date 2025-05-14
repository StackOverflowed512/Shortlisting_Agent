import requests
import json
import logging
from config import OLLAMA_BASE_URL, OLLAMA_LLM_MODEL, OLLAMA_EMBEDDING_MODEL

logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(self, base_url=OLLAMA_BASE_URL, llm_model=OLLAMA_LLM_MODEL, embedding_model=OLLAMA_EMBEDDING_MODEL):
        self.base_url = base_url
        self.llm_model = llm_model
        self.embedding_model = embedding_model
        self._check_ollama_availability()

    def _check_ollama_availability(self):
        try:
            response = requests.get(self.base_url)
            response.raise_for_status()
            logger.info(f"Successfully connected to Ollama at {self.base_url}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Ollama at {self.base_url}. Ensure Ollama is running. Error: {e}")
            raise ConnectionError(f"Failed to connect to Ollama at {self.base_url}. Ensure Ollama is running.")

    def generate_completion(self, prompt: str, model: str = None, format_json: bool = False) -> str:
        model_to_use = model if model else self.llm_model
        api_url = f"{self.base_url}/api/generate"
        payload = {
            "model": model_to_use,
            "prompt": prompt,
            "stream": False
        }
        if format_json:
            payload["format"] = "json"

        logger.debug(f"Sending generation request to Ollama: {model_to_use}, prompt length: {len(prompt)}")
        try:
            response = requests.post(api_url, json=payload)
            response.raise_for_status()
            response_data = response.json()
            
            # Handle potential JSON parsing issues if format_json=True
            if format_json:
                try:
                    # The actual content is in response_data['response'], which is a string representation of JSON
                    return json.loads(response_data.get("response", "{}"))
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response from Ollama: {e}. Response: {response_data.get('response')}")
                    # Fallback or re-attempt could be implemented here
                    # For now, return the raw string if parsing fails, or an empty dict
                    return response_data.get("response", "{}") if isinstance(response_data.get("response"), str) else {}

            return response_data.get("response", "")
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama API request failed: {e}")
            logger.error(f"Response text: {response.text if 'response' in locals() else 'No response object'}")
            return "" # Or raise an exception

    def generate_embedding(self, text: str, model: str = None) -> list[float]:
        model_to_use = model if model else self.embedding_model
        api_url = f"{self.base_url}/api/embeddings"
        payload = {
            "model": model_to_use,
            "prompt": text
        }
        logger.debug(f"Sending embedding request to Ollama: {model_to_use}, text length: {len(text)}")
        try:
            response = requests.post(api_url, json=payload)
            response.raise_for_status()
            response_data = response.json()
            return response_data.get("embedding", [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama API embedding request failed: {e}")
            logger.error(f"Response text: {response.text if 'response' in locals() else 'No response object'}")

            return [] # Or raise an exception

if __name__ == '__main__':
    # Basic test
    logging.basicConfig(level=logging.INFO)
    try:
        client = OllamaClient()
        
        # Test LLM generation
        prompt_jd = "Summarize the following job description focusing on skills, experience, and education. Output in JSON format with keys 'required_skills', 'experience_years', 'education_level', 'responsibilities'. Job Description: We are looking for a Python Developer with 5 years of experience in web development, a Bachelor's degree in CS, and expertise in Django and Flask."
        summary = client.generate_completion(prompt_jd, format_json=True)
        print("JD Summary:", summary)

        # Test embedding
        embedding = client.generate_embedding("Hello, world!")
        print("Embedding (first 5 dimensions):", embedding[:5] if embedding else "Failed to get embedding")
        print(f"Embedding dimension: {len(embedding)}")

    except ConnectionError as e:
        print(e)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")