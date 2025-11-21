from flask import Flask, send_from_directory, request
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Absolute path to your saved_images directory
MITMPROXY_AD_PULL_PROJECT_DIR = os.getenv('MITMPROXY_AD_PULL_PROJECT_DIR')
SAVED_IMAGES_DIR = os.path.join(MITMPROXY_AD_PULL_PROJECT_DIR.rstrip('/'), 'saved_images')

DATABASE_FILEPATH = os.path.join(MITMPROXY_AD_PULL_PROJECT_DIR.rstrip('/'), "extracted_texts.db")

@app.route('/saved_images/<path:filename>')
def serve_saved_image(filename):
    return send_from_directory(SAVED_IMAGES_DIR, filename)

def get_db_connection():
    conn = sqlite3.connect(DATABASE_FILEPATH)
    conn.row_factory = sqlite3.Row  # makes rows behave like dictionaries
    return conn

@app.route('/')
def get_unclassified_imgs_w_text_data():
    conn = get_db_connection()
    rows = conn.execute("SELECT it.id AS id, it.full_filepath, text, text_script, is_suspected_ad_manual FROM image_texts it LEFT JOIN image_saved_data isd ON isd.full_filepath = it.full_filepath WHERE is_suspected_ad_manual IS NULL ORDER BY RANDOM()").fetchall()
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
