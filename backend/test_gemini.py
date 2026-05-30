from dotenv import load_dotenv
import os

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

prompt = """
Analyze this resume for the role: ML Engineer.

Resume:
Python developer with ML experience.

Return ONLY in this format:

Role Match Score: XX/100

Current Profile:
Backend Developer / ML Beginner / Data Analyst / etc.

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

Keep the response under 120 words.
Be concise and direct.
"""

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt
)

print(response.text)