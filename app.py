from flask import Flask, send_from_directory
import sqlite3

app = Flask(__name__)

DATABASE = "extracted_texts.db"

# Absolute path to your saved_images directory
SAVED_IMAGES_DIR = '/Users/irisglaze/code/thesis/MitmProxyAdPull/saved_images'

@app.route('/saved_images/<path:filename>')
def serve_saved_image(filename):
    return send_from_directory(SAVED_IMAGES_DIR, filename)

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # makes rows behave like dictionaries
    return conn

@app.route('/')
def hello_world():  # put application's code here
    conn = get_db_connection()
    rows = conn.execute("SELECT it.id AS id, it.full_filepath, is_suspected_ad_manual FROM image_texts it LEFT JOIN image_saved_data isd ON isd.full_filepath = it.full_filepath WHERE is_suspected_ad_manual IS NULL").fetchall()
    conn.close()

    # convert query results into a string or JSON
    result = [dict(row) for row in rows]
    return {"data": result}  # Flask automatically JSON-encodes dicts


if __name__ == '__main__':
    app.run()
