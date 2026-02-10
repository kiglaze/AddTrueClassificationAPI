import textwrap
from typing import Any

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
    user_param_value = request.args.get('user') or None
    if user_param_value is not None:
        conn = get_db_connection()

        query = textwrap.dedent("""\
            SELECT it.id AS id, it.full_filepath, wv.website_url, text, wv.screenshot_filepath, wv.video_filepath FROM image_texts it
            LEFT JOIN image_saved_data isd ON isd.full_filepath = it.full_filepath
            LEFT JOIN websites_visited wv ON wv.website_url = isd.referrer_url
            WHERE it.full_filepath NOT IN (
                SELECT DISTINCT full_filepath FROM image_ground_truth igt
                WHERE igt.classification_issuer = ? AND igt.is_suspected_ad_manual IN (0, 1)
            ) AND it.full_filepath IN (
                SELECT full_filepath FROM users_ground_truth_assignments WHERE classification_issuer = ?
            ) ORDER BY RANDOM()
        """)

        params = (user_param_value, user_param_value)

        rows = conn.execute(query, params).fetchall()

        conn.close()

        # convert query results into a string or JSON
        result = [dict(row) for row in rows]
    else:
        result = []
    return {"data": result}  # Flask automatically JSON-encodes dicts

@app.route('/results')
def get_ground_truth_results():
    conn = get_db_connection()
    query = textwrap.dedent("""\
        SELECT full_filepath, is_suspected_ad_manual, classification_issuer FROM image_ground_truth
        WHERE classification_issuer IS NOT NULL AND is_suspected_ad_manual IN (0, 1)
        AND image_ground_truth.full_filepath IN (
            SELECT DISTINCT full_filepath FROM users_ground_truth_assignments
        )
        ORDER BY full_filepath, classification_issuer
    """)
    params = ()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    result = [dict(row) for row in rows]
    return {"data": result}

# Endpoint to update classification
# Data is sent as JSON with 'classification' and 'filepath' fields
@app.route('/update_classification', methods=['POST'])
def update_classification():
    data = request.get_json()
    if not data or 'classification' not in data or 'filepath' not in data:
        return {'error': 'Missing classification or filepath in request'}, 400
    classification = data['classification']
    filepath = data['filepath']
    is_flagged_issue = data.get('flag_issue', False)
    notes = data.get('notes', None)
    classification_issuer = data.get('classification_issuer', 'unknown')
    is_ad_marker = data.get('is_ad_marker', False)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT OR IGNORE INTO classifier_users (classification_issuer) VALUES (?)",
            (classification_issuer,)
        )
        cur.execute(
            """
            INSERT INTO image_ground_truth
                (full_filepath, is_suspected_ad_manual, classification_issuer, flag_issue, notes, is_ad_marker)
            VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(classification_issuer, full_filepath)
            DO
            UPDATE SET
                is_suspected_ad_manual = excluded.is_suspected_ad_manual,
                flag_issue = excluded.flag_issue,
                notes = excluded.notes,
                is_ad_marker = excluded.is_ad_marker,
                updated_at = CURRENT_TIMESTAMP
            """,
            (filepath, classification, classification_issuer, is_flagged_issue, notes, is_ad_marker),
        )
        conn.commit()
        updated = cur.rowcount
    except Exception as e:
        conn.rollback()
        return {'error': f'Database error: {str(e)}'}, 500
    finally:
        conn.close()

    if updated == 0:
        return {'error': 'No record updated'}, 404

    return {'success': True, 'updated': updated}

@app.route('/user_options')
def get_user_options():
    conn = get_db_connection()
    query = textwrap.dedent("""\
        SELECT classification_issuer FROM classifier_users
        ORDER BY classification_issuer
    """)
    params = ()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    result = [row['classification_issuer'] for row in rows]
    return {"data": result}

if __name__ == '__main__':
    app.run(port=5000)
