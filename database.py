import sqlite3
from datetime import datetime
import json

DB_PATH = "documents.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT,
            type_of_document TEXT,
            key_fields TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_document(file_name: str, doc_type: str, key_fields: dict):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO documents (file_name, type_of_document, key_fields, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            file_name,
            doc_type,
            json.dumps(key_fields),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    conn.commit()
    conn.close()

def fetch_all_documents():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, file_name, type_of_document, key_fields, created_at FROM documents"
    )
    rows = cur.fetchall()
    conn.close()

    result = []
    for row in rows:
        sno, file_name, doc_type, key_fields_json, created_at = row
        result.append(
            {
                "sno": sno,
                "name_of_document": file_name,
                "type_of_document": doc_type,
                "key_fields": key_fields_json,
                "datetime": created_at,
            }
        )
    return result

if __name__ == "__main__":
    init_db()
    print("DB ready.")
