import fitz
from google import genai
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Gemini Client
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

# PDF Text Extractor
def extract_text(pdf_path):
    doc = fitz.open(pdf_path)

    text = ""

    for page in doc:
        text += page.get_text()

    return text


# Read Resume
resume_text = extract_text("resume.pdf")

# User Target Role
target_role = input("Enter target role: ")

# Prompt
prompt = f"""
You are an expert recruiter.

Target Role: {target_role}

Resume:
{resume_text}

IMPORTANT:
Score should be based ONLY on suitability for the target role,
not generic ATS keywords.

Return ONLY:

Role Match Score: XX/100

Current Profile:
(1 line)

Missing Skills:
- skill 1
- skill 2
- skill 3

Missing Project Types:
- project 1
- project 2

Top 3 Improvements:
- improvement 1
- improvement 2
- improvement 3

Keep answer under 120 words.
Score should be based ONLY on suitability for the target role, not generic ATS keywords.
"""

# Gemini Analysis
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt
)

print(response.text)