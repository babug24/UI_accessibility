import sqlite3
import os
from typing import List, Dict

DB_PATH = os.getenv('VINX_DB_PATH', os.path.join(os.path.dirname(__file__), 'vinx_ultra.db'))

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


def save_message(role: str, content: str, metadata: dict = None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO messages (role, content, metadata) VALUES (?, ?, ?)',
              (role, content, json_safe(metadata)))
    conn.commit()
    conn.close()


def json_safe(obj):
    try:
        import json
        return json.dumps(obj) if obj is not None else None
    except Exception:
        return None


def get_history(limit: int = 200) -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, role, content, metadata, created_at FROM messages ORDER BY id DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    conn.close()
    out = []
    for r in rows[::-1]:
        out.append({'id': r[0], 'role': r[1], 'content': r[2], 'metadata': r[3], 'created_at': r[4]})
    return out
