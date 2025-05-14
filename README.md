# Multi-Agent Recruitment Automation System

This project implements a multi-agent system for automating various stages of the recruitment process using on-premise LLMs (via Ollama), embedding models, and a SQLite database.

## Features

-   **Job Description Summarizer Agent**: Parses raw JD text and extracts key information (skills, experience, education, responsibilities) into a structured JSON format.
-   **Resume Extractor & Matcher Agent**:
    -   Extracts text from PDF and DOCX resumes.
    -   Uses an LLM to parse structured data (name, email, skills, experience, education) from resume text.
    -   Compares resumes with the summarized JD using embedding-based similarity (cosine similarity).
-   **Shortlister Agent**: Shortlists candidates based on a configurable match score threshold (e.g., >= 0.75).
-   **Interview Scheduler Agent**: Sends mock or real interview invitation emails to shortlisted candidates (configurable).
-   **SQLite Database**: Stores job descriptions, candidate information, match scores, statuses, and logs.
-   **Ollama Integration**: Leverages local LLMs (e.g., Llama3) for text generation/summarization and embedding models (e.g., `nomic-embed-text`) for semantic matching.

