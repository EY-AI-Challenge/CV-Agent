import json
import os
import tempfile

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

import operations

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
CORS(app)

# Ensure DB schema exists
operations.db_connection.execute("""
    CREATE TABLE IF NOT EXISTS evaluations (
        job_name TEXT NOT NULL,
        cv_email TEXT NOT NULL,
        results  BLOB,
        PRIMARY KEY (job_name, cv_email)
    )
""")
operations.db_connection.commit()


# --- Serve frontend ---

@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/src/<path:filename>')
def src_files(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'src'), filename)


# --- API ---

@app.route('/api/match', methods=['POST'])
def match():
    job_name = request.form.get('job_name', '').strip()
    cv_files = request.files.getlist('cv_files')

    if not job_name:
        return jsonify({"error": "job_name is required"}), 400
    if not cv_files:
        return jsonify({"error": "No CV files uploaded"}), 400

    results = []

    for cv_file in cv_files:
        cv_id = cv_file.filename

        force = request.form.get('force') == 'true'

        if not force:
            cached = operations.queryResults(job_name, cv_id)
            if cached:
                cached['_cached'] = True
                results.append(cached)
                continue

        ext = os.path.splitext(cv_file.filename)[1] or '.pdf'
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            cv_file.save(tmp.name)
            tmp_path = tmp.name

        try:
            cv_text = operations.extract_pdf_text(tmp_path)
        finally:
            os.unlink(tmp_path)

        result = operations.agent_request_text(cv_text, job_name)

        # n8n wraps the agent output as {"output": "<JSON string>"}
        if 'output' in result and isinstance(result['output'], str):
            try:
                result = json.loads(result['output'])
            except Exception:
                pass

        result['_filename'] = cv_file.filename

        if 'error' not in result:
            existing = operations.queryResults(job_name, cv_id)
            if existing:
                operations.updateResults(job_name, cv_id, result)
            else:
                operations.storeResults(job_name, cv_id, result)

        results.append(result)

    return jsonify(results)


@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    job_name = request.json.get('job_name') if request.json else None
    if job_name:
        operations.db_connection.execute(
            "DELETE FROM evaluations WHERE job_name = ?", (job_name,))
    else:
        operations.db_connection.execute("DELETE FROM evaluations")
    operations.db_connection.commit()
    return jsonify({"ok": True})


if __name__ == '__main__':
    app.run(port=8080, debug=True)
