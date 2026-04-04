
import sys
import os
from pathlib import Path

BASE_DIR    = Path(__file__).resolve().parent.parent
CRAWLER_DIR = BASE_DIR / "crawler"
MODEL_PATH  = BASE_DIR / "models" / "Llama-3.2-3B-Instruct-f16.gguf"

print(CRAWLER_DIR)
if not CRAWLER_DIR.exists():
    print(f"\n  [ERROR] Crawler directory not found:\n  {CRAWLER_DIR}\n")
    sys.exit(1)

if str(CRAWLER_DIR) not in sys.path:
    sys.path.insert(0, str(CRAWLER_DIR))

if not MODEL_PATH.exists():
    print(f"\n  [ERROR] Model not found:\n  {MODEL_PATH}")
    print(  "  Set MODEL_PATH in meshi.py to point at your .gguf file.\n")
    sys.exit(1)

try:
    from llama_cpp import Llama
    import llama_cpp
except ImportError:
    print("\n  [ERROR] llama_cpp is not installed.")
    print(  "  Run:  pip install llama-cpp-python\n")
    sys.exit(1)

from crawl import start_crawler

gpu_available = llama_cpp.llama_cpp.llama_supports_gpu_offload()


llm = Llama(
    model_path=str(MODEL_PATH),
    n_gpu_layers=16 if gpu_available else 3,
    n_ctx=2048,
    verbose=False,
)

if __name__ == "__main__":
    try:
        start_crawler(llm)
    except KeyboardInterrupt:
        print("\n  [meshi] terminated.")
