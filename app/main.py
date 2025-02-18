import io
import json
import os
import traceback
from typing import List


import openai
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import pandas as pd

from app.logger import app_logger as logger
from app.utils import DocxReader, PdfReader, OpenAIClient
from app.config import settings

app = FastAPI(
    title="Resume Ranking API",
    description="API to extract job ranking criteria and score resumes against them",
    version="1.0.0",
)

LLM_CLIENT = OpenAIClient(settings.OPENAI_API_KEY)

FILE_TYPE_TO_EXTRACTOR = {
    ".pdf": PdfReader,
    ".docx": DocxReader,
}


async def get_extractor(file: UploadFile):
    """
    Detect file type by extension and return the appropriate extractor class.
    """
    filename = file.filename.lower()
    _, ext = os.path.splitext(filename)
    if ext not in FILE_TYPE_TO_EXTRACTOR:
        await logger.error(f"Unsupported file type: {ext}")
        raise ValueError(f"Unsupported file type: {ext}")
    return FILE_TYPE_TO_EXTRACTOR[ext]


@app.post("/extract-criteria", summary="Extract Ranking Criteria from Job Description")
async def extract_criteria_endpoint(file: UploadFile = File(...)):
    """
    Upload a job description file (PDF or DOCX) and extract key ranking criteria.

    **Parameters:**
    - **file**: Job description file in PDF or DOCX format.

    **Returns:**
    - A JSON object with a key `criteria` containing a list of extracted criteria.

    **Example Output:**
    ```json
    {
      "criteria": [
        "Must have certification XYZ",
        "5+ years of experience in Python development",
        "Strong background in Machine Learning"
      ]
    }
    ```
    """
    try:
        extractor_class = await get_extractor(file)
        tmp_path = f"/tmp/{file.filename}"
        with open(tmp_path, "wb") as f:
            f.write(file.file.read())
        extractor = extractor_class(tmp_path)
        base64_images = extractor.convert_to_base64()
        criteria = LLM_CLIENT.extract_criteria_json(base64_images)
        return {"criteria": criteria}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@app.post("/score-resumes", summary="Score Resumes Against Extracted Criteria")
async def score_resumes_endpoint(
    criteria: str = Form(...),
    files: List[UploadFile] = File(...)
):
    """
    Upload multiple resume files (PDF or DOCX) and score them based on provided ranking criteria.

    **Parameters:**
    - **criteria**: A JSON-formatted string representing a list of criteria.
    - **files**: List of resume files in PDF or DOCX format.

    **Returns:**
    - A CSV file (downloadable) with columns for Candidate Name, individual scores for each criterion, and Total Score.

    **Example CSV:**

    | Candidate Name | Certification XYZ | Python Experience | Machine Learning | Total Score |
    |----------------|-------------------|-------------------|------------------|-------------|
    | John Doe       | 5                 | 4                 | 4                | 13          |
    | Jane Smith     | 4                 | 3                 | 5                | 12          |
    """
    try:
        # Parse the criteria from the JSON-formatted string
        criteria_list = json.loads(criteria)
    except Exception as e:
        await logger.error(f"Invalid criteria format: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid criteria format. Must be a JSON list of strings."},
        )

    resumes_base64 = []
    candidate_names = []
    for file in files:
        try:
            extractor_class = await get_extractor(file)
            tmp_path = f"/tmp/{file.filename}"
            with open(tmp_path, "wb") as f:
                f.write(file.file.read())
            extractor = extractor_class(tmp_path)
            base64_images = extractor.convert_to_base64()
            resumes_base64.append(base64_images)
            # Extract candidate name from filename (remove extension)
            candidate_name = os.path.splitext(file.filename)[0]
            candidate_names.append(candidate_name)
        except Exception as e:
            await logger.error(f"Error processing file {file.filename}: {str(e)}")
            return JSONResponse(status_code=400, content={"error": f"Error processing file {file.filename}: {str(e)}"})

    try:
        # Score all resumes using the LLM client
        score_responses = LLM_CLIENT.score_multiple_resumes_against_criteria(criteria_list, resumes_base64)
    except Exception as e:
        await logger.error(f"Error scoring resumes: {traceback.format_exc()}")
        return JSONResponse(status_code=400, content={"error": f"Error scoring resumes: {str(e)}"})

    # Build the results list for CSV output.
    # Assume each score_response is an instance of ScoreResponse.
    results = []
    for idx, score_response in enumerate(score_responses):
        # Use candidate name from LLM if provided, else fallback to filename.
        candidate_name = score_response.candidate_name or candidate_names[idx]
        entry = {"Candidate Name": candidate_name}
        # Merge individual scores into the entry
        for crit, score in score_response.scores.items():
            entry[crit] = score
        entry["Total Score"] = score_response.total_score
        results.append(entry)

    # Create CSV output using pandas
    df = pd.DataFrame(results)
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    return StreamingResponse(
        iter([csv_buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=resume_scores.csv"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)