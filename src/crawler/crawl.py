import sys
import time
import json
import re
import random
import sqlite3
import threading
import queue
from collections import deque
from pathlib import Path

import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin

inference_queue: queue.Queue = queue.Queue()
db_queue:        queue.Queue = queue.Queue()
_db_lock = threading.Lock()

LOGS_DIR = Path(__file__).parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

RST  = "\033[0m";  BOLD = "\033[1m";  DIM  = "\033[2m"
RED  = "\033[31m"; GRN  = "\033[32m"; YLW  = "\033[33m"; CYN  = "\033[36m"

# ── Live Display ──────────────────────────────────────────────────────────────
class LiveDisplay:
    _LABELS = [
        f"{BOLD}{CYN} CRWLR {RST}│ ",
        f"{BOLD}{GRN} INFRC {RST}│ ",
        f"{BOLD}{YLW} DTABS {RST}│ ",
        f"{BOLD}{DIM} STATS {RST}│ ",
    ]
    _BENTO_W = 12

    def __init__(self):
        self._lines = ["waiting...", "waiting...", "waiting...", ""]
        self._lock = threading.Lock()
        self._drawn = False
        self._bp = 0
        self._bd = 1
        self._t0 = time.time()
        self._saved = 0
        self.errs = {"crawler": 0, "llm": 0, "db": 0}
        self.active = True
        threading.Thread(target=self._bento_loop, daemon=True).start()

    def set(self, row: int, text: str):
        with self._lock:
            self._lines[row] = text
            self._draw()

    def error(self, src, msg):
        self.errs[src] = self.errs.get(src, 0) + 1
        with open(LOGS_DIR / "errors.log", "a") as f:
            f.write(f"[{src}] {msg}\n")

    def _draw(self):
        if self._drawn: 
            sys.stdout.write("\033[4A")
        
        for lbl, txt in zip(self._LABELS, self._lines):
           
            clean_txt = str(txt).strip().replace("\n", " ")[:80]
            sys.stdout.write(f"\r\033[K{lbl}{clean_txt}\n")
        
        sys.stdout.flush()
        self._drawn = True

    def _bento_loop(self):
        while self.active:
            elapsed = int(time.time() - self._t0)
            m, s = (elapsed % 3600) // 60, elapsed % 60
            bar = list("·" * self._BENTO_W)
            bar[self._bp] = "🍱"
            stats = f"[{''.join(bar)}] {m:02d}:{s:02d} | saved: {self._saved} | errs: {sum(self.errs.values())}"
            self.set(3, stats)
            
            self._bp += self._bd
            if self._bp >= self._BENTO_W - 1 or self._bp <= 0: 
                self._bd *= -1
            time.sleep(0.15)

def run_inference(llm, text: str) -> dict:
    example_json = {
        "Title": "Garlic Butter Pasta",
        "Author": "Chef Mario",
        "Time": 15,
        "MainIngredient": "Pasta",
        "Nutrition": "450 kcal, 12g fat, 70g carbs, 15g protein",
        "Cuisine": "Italian",
        "Ingredients": "1. 1 serving dry pasta. 2. 2 cloves garlic. 3. 1 tbspoon butter.",
        "Instructions": "1. Boil pasta. 2. Sauté garlic in butter. 3. Toss together."
    }

    prompt = (
    "You are a precise recipe extraction system.\n"
    "Your task is to extract a COMPLETE and DETAILED recipe into JSON.\n\n"

    "CRITICAL RULES:\n"
    "- Output ONLY valid JSON. No explanations.\n"
    "- Use EXACT keys:\n"
    "  Title, Author, Time, MainIngredient, Nutrition, Cuisine, Instructions\n"
    "- DO NOT summarize or shorten instructions.\n"
    "- PRESERVE all important cooking details.\n\n"

    "INSTRUCTIONS FIELD REQUIREMENTS (VERY IMPORTANT):\n"
    "- Output Instructions as a SINGLE STRING, not a list.\n"
    "- Use a numbered format inside the string (e.g., '1. Step one. 2. Step two.').\n"
    "- DO NOT output a JSON array as the Instructions value.\n"
    "- Include ALL measurements (e.g., 1 tbsp, 200g, 2 cups).\n"
    "- Include ALL timing (e.g., cook for 10 minutes, simmer 5 min).\n"
    "- Include ALL tools (pan, oven, skillet, blender, etc.).\n"
    "- Include ALL techniques (sauté, whisk, roast, simmer, etc.).\n"
    "- Include ALL seasonings and ingredients mentioned.\n"
    "- Include ALL fats and oils used to cook.\n"
    "- Describe how to prepare and cook each subcomponent (e.g., sauce, filling, garnish).\n"
    "- Do NOT compress steps into one sentence.\n"
    "- Each step should be clear and actionable.\n\n"

    "FIELD EXTRACTION RULES:\n"
    "- Time = total cooking time in minutes (number only if possible).\n"
    "- If unknown, use \"Unknown\".\n"
    "- MainIngredient = primary ingredient of the dish.\n"
    "- Nutrition = include calories and macros if listed, otherwise \"Unknown\".\n"
    "- Cuisine = type of cuisine if identifiable, otherwise \"Unknown\".\n\n"
    "- Ingredients = exhaustive string enumeration of all ingredients with quantities and measurements.\n"
    "EXAMPLE FORMAT (structure only, not content):\n"
    f"{json.dumps(example_json)}\n\n"

    "TEXT:\n"
    f"{text[:3000]}"
    )

    resp = llm.create_chat_completion(
        messages=[
            {"role": "system", "content": "You are a JSON data extraction tool. Output ONLY valid JSON."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1200,
        temperature=0.0,
    )

    content = resp["choices"][0]["message"]["content"]
    try:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match: 
            raise ValueError("No JSON found")
        data = json.loads(match.group())
        
        for key in ["Title", "Author", "Time", "MainIngredient", "Nutrition", "Cuisine", "Instructions", "Ingredients"]:
            if key not in data:
                data[key] = "Unknown"
        return data
    except Exception as e:
        with open(LOGS_DIR / f"raw_fail_{int(time.time())}.txt", "w") as f:
            f.write(content)
        raise 


def db_worker(display: LiveDisplay):
    while True:
        item = db_queue.get()
        if item is None: 
            db_queue.task_done()
            break
        
        data, url = item
        try:
            raw_time = data.get("Time", 0)
            clean_time = int(re.sub(r"\D", "", str(raw_time))) if raw_time else 0

            with _db_lock:
                from config import DB_NAME
                conn = sqlite3.connect(DB_NAME)
                conn.execute(
                    "INSERT OR IGNORE INTO Meshi (source_url, author, title, total_time, main_ingredient, nutritional_info, cuisine, ingredients, instructions) VALUES (?,?,?,?,?,?,?,?,?)",
                    (url, data.get("Author"), data.get("Title"), clean_time, data.get("MainIngredient"), data.get("Nutrition"), data.get("Cuisine"), data.get("Ingredients"), data.get("Instructions"))
                )
                conn.commit()
                conn.close()
            
            display._saved += 1
            display.set(2, f"Saved: {data.get('Title', 'Unknown')[:40]}")
        except Exception as e:
            display.error("db", str(e))
        finally:
            db_queue.task_done()

def inference_worker(llm, display: LiveDisplay):
    while True:
        task = inference_queue.get()
        if task is None:
            db_queue.put(None)
            inference_queue.task_done()
            break
        
        txt_path, url = task
        display.set(1, f"Processing {Path(txt_path).stem[:40]}")
        try:
            text = Path(txt_path).read_text(encoding="utf-8")
            data = run_inference(llm, text)
            db_queue.put((data, url))
        except Exception as e:
            display.error("llm", str(e))
        finally:
            inference_queue.task_done()

def _crawler(display: LiveDisplay, stop: threading.Event):
    from config import SEEDS, HEADERS, CRAWL_DELAY
    from crawl_eval import normalize, is_recipe_page, is_crawlable
    from crawlio import load_visited, append_visited, save_raw_txt, extract_text

    visited = load_visited()
    seen = set(visited)
    frontier = deque(n for u in SEEDS if (n := normalize(u)) not in seen)

    while not stop.is_set():
        if not frontier:
            stop.wait(5)
            continue

        url = frontier.popleft()
        if url in visited: continue

        display.set(0, f"fetching {url[:50]}...")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=12)
            resp.raise_for_status()
            visited.add(url)
            append_visited(url) 

            soup = BeautifulSoup(resp.text, "html.parser")
            if is_recipe_page(soup):
                display.set(0, f"{GRN}recipe ✓ {RST} {url[:50]}")
                path = save_raw_txt(extract_text(soup), resp.url)
                inference_queue.put((path, resp.url))
            
            for a in soup.find_all("a", href=True):
                n = normalize(urljoin(resp.url, a["href"]))
                if is_crawlable(n) and n not in seen:
                    seen.add(n)
                    frontier.append(n)
        except Exception as exc:
            display.error("crawler", str(exc))
        
        stop.wait(random.uniform(*CRAWL_DELAY))

def start_crawler(llm):
    from crawlio import init_db
    from config import DB_NAME
    init_db()
    
    display = LiveDisplay()
    stop_event = threading.Event()
    print("\033[H\033[J", end="")
    sys.stdout.write("\033[2J\033[H") 
    print(f"{BOLD}{CYN}  🍱 om nom nom.{RST}\n")

    t_infer = threading.Thread(target=inference_worker, args=(llm, display), daemon=True)
    t_db = threading.Thread(target=db_worker, args=(display,), daemon=True)
    t_crawl = threading.Thread(target=_crawler, args=(display, stop_event), daemon=True)

    t_infer.start()
    t_db.start()
    t_crawl.start()

    try:
        while t_crawl.is_alive():
            t_crawl.join(timeout=0.1)
    except KeyboardInterrupt:
        display.set(3, f"{RED}Stopping... flushing queues...{RST}")
        stop_event.set()
        t_crawl.join()

    inference_queue.put(None)
    t_infer.join()
    t_db.join()
    display.active = False

    print(f"\n{BOLD}{GRN}  ✓ Done.{RST} Saved {display._saved} recipes to {DB_NAME}\n")