import os
import re
import hashlib
import sqlite3
from urllib.parse import urlparse
from config import *



def init_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS Meshi (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            source_url       TEXT,
            author           TEXT,
            title            TEXT,
            total_time       TEXT,
            main_ingredient  TEXT,
            nutritional_info TEXT,
            cuisine          TEXT,
            instructions     TEXT,
            ingredients      TEXT
        )
    """)
    conn.commit()
    conn.close()



def load_visited() -> set:
    if not os.path.exists(VISITED_FILE):
        return set()
    with open(VISITED_FILE, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def append_visited(url: str):
    with open(VISITED_FILE, "a", encoding="utf-8") as f:
        f.write(url + "\n")



def save_raw_txt(text: str, url: str) -> str:

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    path_part = urlparse(url).path.strip("/").replace("/", "_")[:80]
    slug      = re.sub(r"[^\w\-]", "_", path_part).strip("_") or "recipe"
    url_hash  = hashlib.md5(url.encode()).hexdigest()[:6]

    path = os.path.join(OUTPUT_DIR, f"{slug}_{url_hash}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"SOURCE: {url}\n\n{text}")
    return path



def extract_text(soup) -> str:
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)
