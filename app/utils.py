import os
import base64
import tempfile

from docx2pdf import convert as docx2pdf_convert
from pdf2image import convert_from_path
from PIL import Image
from io import BytesIO

from openai import OpenAI
import instructor
from pydantic import BaseModel, Field


class PdfReader:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path

    def convert_to_images(self) -> list[Image.Image]:
        """Convert PDF pages to images."""
        return convert_from_path(self.pdf_path)

    def convert_to_base64(self) -> list[str]:
        """Convert images to base64-encoded strings."""
        images = self.convert_to_images()
        base64_images = []

        for page in images:
            buffered = BytesIO()
            page.save(buffered, format="JPEG")
            img_bytes = buffered.getvalue()
            img_base64 = base64.b64encode(img_bytes).decode("utf-8")
            base64_images.append(img_base64)
        return base64_images


class DocxReader:
    def __init__(self, docx_path: str):
        self.docx_path = docx_path

    def convert_to_images(self) -> list[Image.Image]:
        """Convert DOCX pages to images by first converting DOCX to PDF then to images."""
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            pdf_output_path = os.path.join(tmp_dir_name, "converted.pdf")
            docx2pdf_convert(self.docx_path, pdf_output_path)
            images = convert_from_path(pdf_output_path)
        return images

    def convert_to_base64(self) -> list[str]:
        """Convert images to base64-encoded strings."""
        images = self.convert_to_images()
        base64_images = []
        for page in images:
            buffered = BytesIO()
            page.save(buffered, format="JPEG")
            img_bytes = buffered.getvalue()
            img_base64 = base64.b64encode(img_bytes).decode("utf-8")
            base64_images.append(img_base64)
        return base64_images


class ExtractionResponse(BaseModel):
    extracted_content: str = Field(..., description="Extracted content from the image.")
    criteria: list[str] = Field(..., description="Extracted criteria from the image.")


EXTRACTION_AND_CRITERIA_PROMPT = """You are a world-class document extractor.
Your task is twofold:
1. Extract the complete textual content from the provided images.
2. Identify key ranking criteria present in the content. These ranking criteria typically include, but are not limited to, skills, certifications, experience, and qualifications. If additional ranking criteria are provided by the user, ensure that those are also identified and extracted.

Your output must adhere strictly to the following JSON schema:

{
    "extracted_content": "<full text extracted from the image>",
    "criteria": ["<criterion1>", "<criterion2>", ...]
}

Where:
- "extracted_content" is a string containing all the text extracted from the images.
- "criteria" is a list of strings, each representing a distinct ranking criterion identified in the content.

Important:
- Only include criteria that are explicitly mentioned or clearly implied in the content.
- Do not add any extra commentary or explanations outside of the JSON structure.
- Ensure the output is valid JSON and follows the exact schema provided.

Begin the extraction process now.
"""


class ScoreResponse(BaseModel):
    candidate_name: str = Field(..., description="Candidate's full name extracted from the resume.")
    scores: dict[str, int] = Field(
        ...,
        description="A dictionary where each key is a criterion and the value is the score (0-5)."
    )
    total_score: int = Field(..., description="Total score computed as the sum of individual scores.")


SCORE_RESUME_PROMPT = """You are an expert resume evaluator.
Your task is to evaluate the resume provided and score it against the following criteria:
{criteria_list}

For each criterion, assign a score between 0 and 5, where:
- 0 means there is no evidence of the criterion in the resume.
- 5 means there is exceptional evidence supporting the criterion.

Also, extract the candidate's full name from the resume.

Your output must be valid JSON and follow exactly this schema:

{
    "candidate_name": "<Candidate's full name>",
    "scores": {
         "<criterion1>": <score>,
         "<criterion2>": <score>,
         ...
    },
    "total_score": <total score>
}

Do not include any additional commentary or explanations. Begin the evaluation now.
"""


class OpenAIClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.patched_client = instructor.from_openai(OpenAI(api_key=api_key))

    def extract_criteria_json(self, base64_images: list[str]) -> list[str]:
        """
        Extract data from a base64-encoded image using OpenAI's API.
        """
        response = self.patched_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": EXTRACTION_AND_CRITERIA_PROMPT,
                },
                {
                    "role": "user",
                    "content": (
                            [
                                {
                                    "type": "text",
                                    "text": "Extract the content from the image and identify key ranking criteria such as skills, certifications, experience, and qualifications.",
                                }
                            ]
                            + [
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                                }
                                for base64_image in base64_images
                            ]
                    ),
                },
            ],
            response_model=ExtractionResponse,
            temperature=0.0,
            max_retries=3,
            timeout=None,
        )
        return response.criteria

    def score_resumes_against_criteria(self, criteria: list[str], base64_images: list[str]) -> ScoreResponse:
        """
        Evaluate a single resume (provided as one or more base64-encoded images)
        against a list of ranking criteria.
        The LLM returns a JSON with the candidate's name, individual scores per criterion, and the total score.
        """
        # Format the criteria list for inclusion in the prompt.
        criteria_list = "\n".join(f"- {criterion}" for criterion in criteria)
        prompt = SCORE_RESUME_PROMPT.format(criteria_list=criteria_list)

        response = self.patched_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": (
                            [
                                {
                                    "type": "text",
                                    "text": "Please evaluate the resume based on the above criteria.",
                                }
                            ]
                            + [
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                                }
                                for base64_image in base64_images
                            ]
                    ),
                },
            ],
            response_model=ScoreResponse,
            temperature=0.0,
            max_retries=3,
            timeout=None,
        )
        return response

    def score_multiple_resumes_against_criteria(self, criteria: list[str], resumes_base64: list[list[str]]) -> list[
        ScoreResponse]:
        """
        Process multiple resumes at once.
        - `criteria` is a list of ranking criteria.
        - `resumes_base64` is a list where each element is a list of base64-encoded images representing a single resume.

        Returns a list of ScoreResponse objects, one per resume.
        """
        score_results = []
        for resume_base64_images in resumes_base64:
            score_response = self.score_resumes_against_criteria(criteria, resume_base64_images)
            score_results.append(score_response)
        return score_results

