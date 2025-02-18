
# **LLMExtractor**

## **Description**

**LLMExtractor** is an AI-powered API designed to extract key ranking criteria from job descriptions (PDF or DOCX format) and score resumes based on those criteria. This API leverages GPT-4 to process and evaluate resumes against various ranking criteria, such as skills, certifications, and experience.

The project includes endpoints for extracting job description criteria and scoring multiple resumes accordingly.

## **Features**

- **Extract Ranking Criteria:** Upload job descriptions in PDF or DOCX format to extract the key ranking criteria.
- **Score Resumes:** Upload multiple resumes (PDF or DOCX format) and score them based on previously extracted criteria.
- **AI-Powered Extraction and Scoring:** Uses OpenAI GPT-4 to extract criteria and evaluate resumes.
  
## **Prerequisites**

- Python 3.12 or above
- Poetry (for dependency management)
  
## **Setup**

### 1. **Clone the repository:**
   ```bash
   git clone https://github.com/NIKHILKUMARREDDY28/LLMExtractor.git
   cd LLMExtractor
   ```

### 2. **Install dependencies with Poetry:**
   Install Poetry (if not already installed):
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```
   Install the project dependencies:
   ```bash
   poetry install
   ```

### 3. **Set up your environment variables:**
   Make sure to set your OpenAI API key in your environment. You can set it using:
   ```bash
   .env
   
    OPENAI_API_KEY=your_openai_api_key
   ```

### 4. **Run the API:**
   Start the FastAPI server:
   ```bash
   python app/main.py
   ```

   The API should now be accessible at `http://localhost:8000`.

## **API Endpoints**

### 1. **Extract Ranking Criteria from Job Description**

**Endpoint:** `POST /extract-criteria`

Upload a job description file (PDF or DOCX), and the API will extract key ranking criteria (skills, certifications, experience, etc.).

**Request:**

- **file**: Job description file (PDF or DOCX)

**Response:**
```json
{
  "criteria": [
    "Must have certification XYZ",
    "5+ years of experience in Python development",
    "Strong background in Machine Learning"
  ]
}
```

### 2. **Score Resumes Against Extracted Criteria**

**Endpoint:** `POST /score-resumes`

Upload multiple resume files (PDF or DOCX format) and provide a list of criteria in JSON format. The API will score the resumes against the criteria.

**Request:**

- **criteria**: JSON-formatted list of extracted criteria.
- **files**: List of resume files (PDF or DOCX).

**Response:**
The response will contain a downloadable CSV with candidate names, scores for each criterion, and the total score.

Example CSV format:
```csv
Candidate Name, Certification XYZ, Python Experience, Machine Learning, Total Score
John Doe, 5, 4, 4, 13
Jane Smith, 4, 3, 5, 12
```

## **Project Structure**

- `main.py`: FastAPI application with endpoints for extracting criteria and scoring resumes.
- `app/logger.py`: Logging utilities.
- `app/utils.py`: Utility functions for file reading and processing.
- `app/config.py`: Configuration settings, including API keys.

## **Dependencies**

This project uses the following dependencies, which are listed in `pyproject.toml`:

- **FastAPI**: Web framework for building the API.
- **Uvicorn**: ASGI server to run the FastAPI app.
- **OpenAI**: OpenAI Python client to interact with GPT models.
- **Pydantic**: Data validation and serialization.
- **Pdf2Image**: Converts PDFs to images.
- **Docx2Pdf**: Converts DOCX files to PDF.
- **Pandas**: Data manipulation and CSV export.
- **Python-dotenv**: For managing environment variables.
- **Loguru**: For logging.
- **Instructor**: OpenAI wrapper for enhanced GPT-4 interaction.

## **License**

This project is licensed under the MIT License.

## **Contact**

For any questions or inquiries, please contact [NIKHIL KUMAR REDDY](mailto:nikhilkumar.m@skil.ai).

---
