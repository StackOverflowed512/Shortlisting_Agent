# Multi-Agent Recruitment Automation System

An intelligent recruitment automation system that leverages local LLMs (via Ollama) and embedding models to streamline the hiring process.

## 🌟 Features

### Core Functionality

-   Automated processing of job descriptions and resumes
-   Intelligent candidate matching using semantic similarity
-   Automated shortlisting based on configurable thresholds
-   Interview scheduling and email communications

### Agent Architecture

-   **JD Summarizer Agent**: Extracts structured information from job descriptions
-   **Resume Matcher Agent**: Processes resumes and calculates match scores
-   **Shortlister Agent**: Automatically identifies top candidates
-   **Interview Scheduler Agent**: Manages interview communications

### Technical Features

-   Local LLM processing via Ollama
-   Embedding-based semantic matching
-   SQLite database for data persistence
-   Support for PDF and DOCX resumes
-   Configurable email integration
-   Comprehensive logging system

## 🚀 Getting Started

### Prerequisites

1.  Python 3.8+
2.  [Ollama](https://ollama.ai/) installed and running
3.  Required LLM models:

    ```bash
    ollama pull llama3
    ollama pull nomic-embed-text
    ```

### Installation

1.  Clone the repository:

    ```bash
    git clone https://github.com/yourusername/recruitment-automation.git
    cd recruitment-automation
    ```

2.  Create and activate virtual environment:

    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # Linux/Mac
    source venv/bin/activate
    ```

3.  Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

4.  Configure environment variables:
    -   Copy `.env.example` to `.env`
    -   Update email settings if needed

### Project Structure

```
recruitment-automation/
├── agents/                 # Agent implementations
├── utils/                  # Utility modules
├── data/                  
│   ├── CVs/               # Place resumes here
│   └── job_descriptions.csv
├── database/              # SQLite database
├── logs/                  # Application logs
├── config.py             # Configuration
├── setup_db.py          # Database setup
└── main.py              # Main pipeline
```

## 💡 Usage

1.  Prepare Data:
    -   Place resumes (PDF/DOCX) in `data/CVs/`
    -   Create `data/job_descriptions.csv` with columns:
        -   `Job Description` (required)
        -   `Job Title` (optional)

2.  Run the Pipeline:

    ```bash
    python main.py
    ```

3.  Check Results:
    -   View logs in `logs/app.log`
    -   Check database in `database/recruitment.db`
    -   Email notifications sent to candidates (if enabled)

## ⚙️ Configuration

Key settings in `config.py` and `.env`:

```python
# Ollama Settings
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_LLM_MODEL = "llama3:latest"
OLLAMA_EMBEDDING_MODEL = "nomic-embed-text:latest"

# Matching Settings
SHORTLIST_THRESHOLD = 0.75  # Minimum match score

# Email Settings (configure in .env)
ENABLE_EMAIL_SENDING = True/False
```

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1.  Fork the repository
2.  Create feature branch
3.  Commit changes
4.  Push to branch
5.  Open pull request

## 🔧 Troubleshooting

-   **Ollama Connection Issues**:
    -   Ensure Ollama is running (`ollama serve`)
    -   Check model availability (`ollama list`)

-   **Resume Parsing Fails**:
    -   Verify PDF/DOCX format
    -   Check file permissions

-   **Email Sending Issues**:
    -   Verify SMTP settings
    -   For Gmail, use App Password

