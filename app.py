import textwrap

from flask import Flask, send_from_directory, request
import sqlite3
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

app = Flask(__name__)

# Absolute path to your saved_images directory
MITMPROXY_AD_PULL_PROJECT_DIR = os.getenv('MITMPROXY_AD_PULL_PROJECT_DIR')
SAVED_IMAGES_DIR = os.path.join(MITMPROXY_AD_PULL_PROJECT_DIR.rstrip('/'), 'saved_images')
SCREENSHOTS_DIR = os.path.join(MITMPROXY_AD_PULL_PROJECT_DIR.rstrip('/'), 'browser_client_interface/screenshots')
RECORDINGS_DIR = os.path.join(MITMPROXY_AD_PULL_PROJECT_DIR.rstrip('/'), 'browser_client_interface/recordings')

DATABASE_FILEPATH = os.path.join(MITMPROXY_AD_PULL_PROJECT_DIR.rstrip('/'), "extracted_texts.db")

ALLOWED_FILEPATHS_FILE = os.path.join(Path(__file__).resolve().parent, 'input', 'allowed_image_filepaths.txt')

@app.route('/saved_images/<path:filename>')
def serve_saved_image(filename):
    return send_from_directory(SAVED_IMAGES_DIR, filename)

@app.route('/browser_client_interface/recordings/<path:filename>')
def serve_recording(filename):
    return send_from_directory(RECORDINGS_DIR, filename)

@app.route('/browser_client_interface/screenshots/<path:filename>')
def serve_screenshot(filename):
    return send_from_directory(SCREENSHOTS_DIR, filename)

def get_db_connection():
    conn = sqlite3.connect(DATABASE_FILEPATH)
    conn.row_factory = sqlite3.Row  # makes rows behave like dictionaries
    return conn

@app.route('/')
def get_unclassified_imgs_w_text_data():
    username = request.cookies.get('username') or None

    allowed_filepaths = []
    if os.path.exists(ALLOWED_FILEPATHS_FILE):
        with open(ALLOWED_FILEPATHS_FILE, 'r', encoding='utf-8') as f:
            allowed_filepaths = [line.strip() for line in f if line.strip()]

    conn = get_db_connection()

    query = textwrap.dedent("""\
        SELECT it.id AS id, it.full_filepath, wv.website_url, text, text_script, wv.screenshot_filepath, wv.video_filepath FROM image_texts it
        LEFT JOIN image_saved_data isd ON isd.full_filepath = it.full_filepath
        LEFT JOIN websites_visited wv ON wv.website_url = isd.referrer_url
    """)

    params = ()

    if username is not None:
        query += textwrap.dedent("""\
            WHERE it.full_filepath NOT IN (
                SELECT DISTINCT full_filepath FROM image_ground_truth igt
                WHERE igt.classification_issuer = ? AND igt.is_suspected_ad_manual IN (0, 1)
            )
        """)
        params = (username,)
        if allowed_filepaths:
            query += "\nAND it.full_filepath IN ({})".format(
                ",".join("?" for _ in allowed_filepaths)
            )
            params += tuple(allowed_filepaths)
    elif allowed_filepaths:
        query += "\nWHERE it.full_filepath IN ({})".format(
            ",".join("?" for _ in allowed_filepaths)
        )
        params = tuple(allowed_filepaths)

    query += "\nORDER BY RANDOM()"


    rows = conn.execute(query, params).fetchall()

    conn.close()

    # convert query results into a string or JSON
    result = [dict(row) for row in rows]
    return {"data": result}  # Flask automatically JSON-encodes dicts

# Endpoint to update classification
# Data is sent as JSON with 'classification' and 'filepath' fields
@app.route('/update_classification', methods=['POST'])
def update_classification():
    data = request.get_json()
    if not data or 'classification' not in data or 'filepath' not in data:
        return {'error': 'Missing classification or filepath in request'}, 400
    classification = data['classification']
    filepath = data['filepath']
    classification_issuer = data.get('classification_issuer', 'unknown')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO image_ground_truth
            (full_filepath, is_suspected_ad_manual, classification_issuer)
        VALUES (?, ?, ?) ON CONFLICT(classification_issuer, full_filepath)
        DO
        UPDATE SET
            is_suspected_ad_manual = excluded.is_suspected_ad_manual
        """,
        (filepath, classification, classification_issuer),
    )

    conn.commit()
    updated = cur.rowcount
    conn.close()
    if updated == 0:
        return {'error': 'No record updated'}, 404
    return {'success': True, 'updated': updated}


if __name__ == '__main__':
    app.run(port=5000)
