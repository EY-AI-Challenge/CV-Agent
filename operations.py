import json
import sqlite3
import threading
import time

import requests
from pypdf import PdfReader

# Agent platform endpoint
N8N_BASE_URL = "https://tomassemide.app.n8n.cloud"
WEBHOOK_KEY = "d026b230-dc98-4dda-9295-33fe8042a9b4"
WEBHOOK_PATH = "webhook-test"  # use "webhook" for production
ENDPOINT = f"{N8N_BASE_URL}/{WEBHOOK_PATH}/{WEBHOOK_KEY}"

# SQLite DB connection
db_connection = sqlite3.connect("db.db", check_same_thread=False)
db_cursor = db_connection.cursor()


# Extract text from a PDF file
def extract_pdf_text(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        if not text.strip():
            return f"[Erro: não foi possível extrair texto de {pdf_path}]"
        return text
    except Exception as e:
        return f"[Erro ao ler PDF {pdf_path}: {e}]"


# Send input to agent and return parsed JSON response (PDF paths)
def agent_request(cv_pdf_path, jd_pdf_path):
    cv_text = extract_pdf_text(cv_pdf_path)
    job_description = extract_pdf_text(jd_pdf_path)
    return agent_request_text(cv_text, job_description)


# Send input to agent with raw text (no PDFs needed)
def agent_request_text(cv_text, job_description):
    body = {"cv_text": cv_text, "job_description": job_description}

    try:
        response = requests.post(ENDPOINT, json=body, timeout=60)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": str(e)}


# Query previous evaluation results
def queryResults(job_name, cv_email):
    query = "SELECT results FROM evaluations WHERE job_name = ? AND cv_email = ?;"
    db_cursor.execute(query, (job_name, cv_email))
    row = db_cursor.fetchone()
    return json.loads(row[0]) if row else None


# Store new evaluation results
def storeResults(job_name, cv_email, results):
    query = "INSERT INTO evaluations VALUES (?, ?, ?)"
    db_cursor.execute(query, (job_name, cv_email, json.dumps(results)))
    db_connection.commit()


# Update existing evaluation results
def updateResults(job_name, cv_email, results):
    query = "UPDATE evaluations SET results = ? WHERE job_name = ? AND cv_email = ?;"
    db_cursor.execute(query, (json.dumps(results), job_name, cv_email))
    db_connection.commit()


# Delete evaluation results
def deleteResults(job_name, cv_email):
    query = "DELETE FROM evaluations WHERE job_name = ? AND cv_email = ?;"
    db_cursor.execute(query, (job_name, cv_email))
    db_connection.commit()


# Thread to commit database state every 2 minutes (fallback safety net)
def commitThread():
    while True:
        time.sleep(120)
        db_connection.commit()


# Close DB connection when shutting down
def shutdown():
    db_connection.commit()
    db_cursor.close()
    db_connection.close()


def __init__(self):
    commit_thread = threading.Thread(target=commitThread)
    commit_thread.start()
