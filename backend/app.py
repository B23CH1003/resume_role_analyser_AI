# import fitz
# from google import genai
# from dotenv import load_dotenv
# import os

# # Load .env file
# load_dotenv()

# # Gemini Client
# client = genai.Client(
#     api_key=os.getenv("GEMINI_API_KEY")
# )

# # PDF Text Extractor
# def extract_text(pdf_path):
#     doc = fitz.open(pdf_path)

#     text = ""

#     for page in doc:
#         text += page.get_text()

#     return text


# # Read Resume
# resume_text = extract_text("resume_exp.pdf")

# # User Target Role
# target_role = input("Enter target role: ")

# # Prompt
# prompt = f"""
# You are an expert recruiter.

# Target Role: {target_role}

# Resume:
# {resume_text}

# IMPORTANT:
# Score should be based ONLY on suitability for the target role,
# not generic ATS keywords.

# Return ONLY:

# Role Match Score: XX/100

# Current Profile:
# (1 line)

# Missing Skills:
# - skill 1
# - skill 2
# - skill 3

# Missing Project Types:
# - project 1
# - project 2

# Top 3 Improvements:
# - improvement 1
# - improvement 2
# - improvement 3

# Keep answer under 120 words.
# Score should be based ONLY on suitability for the target role, not generic ATS keywords.
# """

# # Gemini Analysis
# response = client.models.generate_content(
#     model="gemini-2.5-flash",
#     contents=prompt
# )

# print(response.text)
from flask import Flask, request, jsonify, render_template
import fitz
from google import genai
from dotenv import load_dotenv
import os
import requests
import time

load_dotenv()

app = Flask(__name__)

# Clients
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
ANAKIN_API_KEY = os.getenv("ANAKIN_API_KEY")
ANAKIN_BASE = "https://api.anakin.io/v1/wire"

ANAKIN_HEADERS = {
    "X-API-Key": ANAKIN_API_KEY,
    "Content-Type": "application/json"
}

# ─── PDF Extractor ────────────────────────────────────────────
def extract_text(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

# ─── Wire: Poll async task ────────────────────────────────────
def poll_task(task_id, max_wait=30):
    for _ in range(max_wait):
        res = requests.get(f"{ANAKIN_BASE}/task/{task_id}", headers=ANAKIN_HEADERS)
        data = res.json()
        if data.get("status") == "completed":
            return data.get("data")
        elif data.get("status") == "failed":
            return None
        time.sleep(1)
    return None

# ─── Wire: Indeed Job Search ──────────────────────────────────
def fetch_indeed_jobs(role):
    try:
        res = requests.post(f"{ANAKIN_BASE}/task", headers=ANAKIN_HEADERS, json={
            "action_id": "in_search_jobs",
            "params": {"keyword": role, "location": "India"}
        })
        task_id = res.json().get("taskId")
        if not task_id:
            return []
        data = poll_task(task_id)
        jobs = data if isinstance(data, list) else []
        return jobs[:5]  # top 5 jobs
    except Exception as e:
        print(f"Indeed error: {e}")
        return []

# ─── Wire: Indeed Job Details ─────────────────────────────────
def fetch_job_details(job_key):
    try:
        res = requests.post(f"{ANAKIN_BASE}/task", headers=ANAKIN_HEADERS, json={
            "action_id": "in_job_details",
            "params": {"job_key": job_key}
        })
        task_id = res.json().get("taskId")
        if not task_id:
            return ""
        data = poll_task(task_id)
        if data:
            return data.get("description", "")
        return ""
    except Exception as e:
        print(f"Job details error: {e}")
        return ""

# ─── Wire: GitHub User Repos ──────────────────────────────────
def fetch_github_repos(username):
    try:
        res = requests.post(f"{ANAKIN_BASE}/task", headers=ANAKIN_HEADERS, json={
            "action_id": "gh_user_repos",
            "params": {"username": username}
        })
        task_id = res.json().get("taskId")
        if not task_id:
            return []
        data = poll_task(task_id)
        repos = data if isinstance(data, list) else []
        return repos[:10]
    except Exception as e:
        print(f"GitHub error: {e}")
        return []

# ─── Main Analysis ────────────────────────────────────────────
def analyse_resume(resume_text, role, github_username):
    # Fetch Indeed job descriptions
    jobs = fetch_indeed_jobs(role)
    job_descriptions = ""
    for job in jobs:
        job_key = job.get("jobKey") or job.get("job_key") or job.get("id")
        if job_key:
            desc = fetch_job_details(job_key)
            if desc:
                job_descriptions += f"\n---\n{desc}"

    # Fetch GitHub repos
    github_summary = ""
    if github_username:
        repos = fetch_github_repos(github_username)
        if repos:
            github_summary = "GitHub Projects:\n"
            for repo in repos:
                name = repo.get("name", "")
                lang = repo.get("language", "")
                desc = repo.get("description", "")
                github_summary += f"- {name} ({lang}): {desc}\n"

    # Gemini Prompt
    prompt = f"""
You are an expert technical recruiter and career coach.

Target Role: {role}

Resume:
{resume_text}

{github_summary if github_summary else "No GitHub profile provided."}

Real Market Job Descriptions for {role} (from Indeed):
{job_descriptions if job_descriptions else "No job descriptions fetched — use your knowledge of this role."}

INSTRUCTIONS:
- Analyse the resume and GitHub projects against the real market requirements for {role}.
- Score should be ONLY based on suitability for this specific role.
- Be specific, honest, and actionable.

Return EXACTLY in this format:

Role Match Score: XX/100

Current Profile:
(2 lines summary of candidate's current standing)

Top Skills Present:
- skill 1
- skill 2
- skill 3

Missing Skills:
- skill 1
- skill 2
- skill 3
- skill 4

Missing Project Types:
- project type 1
- project type 2

Top 3 Improvements:
1. improvement 1
2. improvement 2
3. improvement 3

Market Insight:
(1-2 lines about what this role actually demands right now)

Keep total response under 200 words.
"""

    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text

# ─── Routes ───────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/analyse", methods=["POST"])
def analyse():
    try:
        resume_file = request.files.get("resume")
        role = request.form.get("role", "").strip()
        github_username = request.form.get("github", "").strip()

        if not resume_file or not role:
            return jsonify({"error": "Resume and target role are required!"}), 400

        resume_text = extract_text(resume_file)
        result = analyse_resume(resume_text, role, github_username)

        return jsonify({"result": result})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)