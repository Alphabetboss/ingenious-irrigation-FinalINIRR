import os
import time
import hashlib
from pathlib import Path
from typing import List
from urllib.parse import urlparse

import requests
from PIL import Image
from tqdm import tqdm
from icrawler.builtin import BingImageCrawler
from duckduckgo_search import DDGS

# =========================
# CONFIG
# =========================
BASE_DIR = Path(r"C:\Users\alpha\OneDrive\Desktop\IngeniousIrrigation\datasets\image_scrape\raw")
TARGET_PER_CLASS = 150
MIN_SIZE = (512, 512)   # drop tiny images
TIMEOUT = 12            # seconds per HTTP request
BING_THREADS = 8

# Class -> list of search phrases (ranked, specific -> broad)
CLASS_QUERIES = {
    "moss": [
        "lawn moss close up photo",
        "moss growing in grass yard",
        "moss patch in lawn"
    ],
    "puddle": [
        "water puddle on grass yard",
        "puddle on lawn",
        "standing water grass"
    ],
    "trees": [
        "front yard trees photo",
        "suburban yard tree",
        "tree in lawn"
    ],
    "bushes": [
        "hedges in yard",
        "bushes in front yard",
        "garden shrubs"
    ],
    "dark_brown_yellow": [
        "lawn drought stressed brown grass",
        "yellow dry grass yard",
        "dead lawn patch"
    ],
    "half_green_half_yellow": [
        "lawn partially yellow grass",
        "patchy lawn green and yellow",
        "uneven lawn color"
    ],
    "perfect_health": [
        "healthy lush green lawn",
        "well maintained green grass yard",
        "golf course fairway lawn"
    ],
    "mushy_mud": [
        "muddy lawn with grass",
        "soggy muddy grass yard",
        "wet muddy turf"
    ],
    "gushing_water": [
        "sprinkler pipe burst gushing water yard",
        "underground water leak lawn",
        "sprinkler geyser leak"
    ],
    "people": [
        "people walking on lawn",
        "child running in yard",
        "person on grass yard"
    ],
}

BING_FILTERS = dict(
    type="photo",
    color="color",
    size="large",
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# =========================
# HELPERS
# =========================
def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def is_valid_image(path: Path) -> bool:
    try:
        if not path.exists() or path.stat().st_size < 10_000:
            return False
        with Image.open(path) as im:
            im.verify()   # structural check
        with Image.open(path) as im:
            w, h = im.size
        return (w >= MIN_SIZE[0] and h >= MIN_SIZE[1])
    except Exception:
        return False

def count_valid_images(folder: Path) -> int:
    return sum(1 for p in folder.glob("*") if p.suffix.lower() in ALLOWED_EXTS and is_valid_image(p))

def hashed_name(url: str, ext_fallback: str = ".jpg") -> str:
    h = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
    ext = os.path.splitext(urlparse(url).path)[1].lower()
    if ext not in ALLOWED_EXTS:
        ext = ext_fallback
    return f"{h}{ext}"

def download_one(url: str, out_dir: Path) -> bool:
    try:
        fname = hashed_name(url)
        out_path = out_dir / fname
        if out_path.exists():
            return True  # already have it

        r = requests.get(url, timeout=TIMEOUT, headers=HEADERS, stream=True)
        if r.status_code != 200 or "image" not in r.headers.get("Content-Type", ""):
            return False

        tmp = out_path.with_suffix(out_path.suffix + ".part")
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        tmp.rename(out_path)

        if not is_valid_image(out_path):
            out_path.unlink(missing_ok=True)
            return False
        return True
    except Exception:
        return False

def ddg_image_urls(query: str, n: int) -> List[str]:
    urls = []
    # safesearch: "moderate" helps avoid junk; size: "Large" to bias bigger imgs
    with DDGS() as ddgs:
        for r in ddgs.images(keywords=query, safesearch="moderate", size="Large"):
            if not r:
                continue
            url = r.get("image")
            if url:
                urls.append(url)
            if len(urls) >= n:
                break
    return urls

def crawl_with_bing(save_dir: Path, queries: List[str], need: int, start_idx=0):
    if need <= 0:
        return
    crawler = BingImageCrawler(
        feeder_threads=1,
        parser_threads=2,
        downloader_threads=BING_THREADS,
        storage={"root_dir": str(save_dir)}
    )
    downloaded_before = count_valid_images(save_dir)
    for q in queries:
        remaining = need - (count_valid_images(save_dir) - downloaded_before)
        if remaining <= 0:
            break
        try:
            crawler.crawl(
                keyword=q,
                max_num=remaining,
                filters=BING_FILTERS,
                file_idx_offset=start_idx + (count_valid_images(save_dir) - downloaded_before)
            )
        except Exception as e:
            print(f"[BING] Error on '{q}': {e}")
        time.sleep(1.0)

def top_up_with_ddg(save_dir: Path, queries: List[str], need: int):
    if need <= 0:
        return
    got = 0
    for q in queries:
        remaining = need - got
        if remaining <= 0:
            break
        urls = ddg_image_urls(q, remaining * 2)  # over-fetch to offset failures
        for url in tqdm(urls, desc=f"[DDG] {q[:30]}…", leave=False):
            if download_one(url, save_dir):
                got += 1
                if got >= need:
                    break
        time.sleep(0.3)

# =========================
# MAIN
# =========================
def main():
    ensure_dir(BASE_DIR)
    for cls, queries in CLASS_QUERIES.items():
        print(f"\n=== Class: {cls} (target {TARGET_PER_CLASS}) ===")
        out_dir = BASE_DIR / cls
        ensure_dir(out_dir)

        have = count_valid_images(out_dir)
        print(f"Existing valid images: {have}")

        # 1) Bing via icrawler
        if have < TARGET_PER_CLASS:
            need = TARGET_PER_CLASS - have
            print(f"[BING] Trying to fetch {need} images…")
            crawl_with_bing(out_dir, queries, need)

        # 2) DuckDuckGo fallback via duckduckgo_search + requests
        have = count_valid_images(out_dir)
        if have < TARGET_PER_CLASS:
            need = TARGET_PER_CLASS - have
            print(f"[DDG] Topping up {need} images…")
            top_up_with_ddg(out_dir, queries, need)

        # Final recount
        final = count_valid_images(out_dir)
        print(f"Final count for {cls}: {final} files")

    print("\nAll done. Folders are in:", BASE_DIR)

if __name__ == "__main__":
    main()
