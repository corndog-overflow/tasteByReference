import os
import json
import re
from urllib.parse import urlparse, urlunparse
from config import *

FORBIDDEN = {"recipe", "recipes", "collection", "collections", "ideas", "kids"}

def has_schema_recipe(soup):
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
            if not isinstance(data, list): data = [data]
            for item in data:
                if "@graph" in item: data.extend(item["@graph"])
                if str(item.get("@type", "")).lower() == "recipe": return True
        except (json.JSONDecodeError, AttributeError): continue
    return False

def is_recipe_page(soup):
    if has_schema_recipe(soup): return True
    text = soup.get_text().lower()
    strong_hits  = sum(1 for kw in RECIPE_STRONG_KW  if kw in text)
    generic_hits = sum(1 for kw in RECIPE_GENERIC_KW if kw in text)
    return strong_hits >= 3 or (strong_hits >= 1 and generic_hits >= 3)

def is_multi_recipe_url(url):
    parsed = urlparse(url)
    path = parsed.path.lower().strip("/")
    if not path: return False

    path_str = f"/{path}/"
    if any(x in path_str for x in ["/collection/", "/guide/", "/category/", "/review/", "/glossary/"]):
        return True

    last_segment = path.split("/")[-1]
    last_segment_words = re.split(r'[^a-z]+', last_segment)
    return any(word in FORBIDDEN for word in last_segment_words)

def normalize(url):
    p = urlparse(url)
    return urlunparse((p.scheme, p.netloc.lower(), p.path.rstrip("/") or "/", "", "", ""))

def is_blocked(url):
    path = urlparse(url).path.lower().rstrip("/")
    segments = path.strip("/").split("/")
    last = segments[-1] if segments else ""
    return last in URL_BLOCKLIST or last in TERMINAL

def is_crawlable(url):
    if any(url.startswith(p) for p in SKIP_PREFIXES): return False
    if is_blocked(url): return False
    ext = os.path.splitext(urlparse(url).path)[1].lower()
    return ext not in SKIP_EXTENSIONS

def url_score(url):
    path = urlparse(url).path.lower()
    path = re.sub(r"\d+", "", path)
    words = [w for w in re.split(r"[^a-z]+", path) if w]
    signals_set = set(RECIPE_URL_SIGNALS)
    return sum(1 for w in words if w in signals_set)
