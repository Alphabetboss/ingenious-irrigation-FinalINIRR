import os
import time
from pathlib import Path
from tqdm import tqdm

# Engines
from icrawler.builtin import BingImageCrawler, DuckduckgoImageCrawler

# =========================
# CONFIG
# =========================
BASE_DIR = Path(r"C:\Users\alpha\OneDrive\Desktop\IngeniousIrrigation\datasets\image_scrape\raw")
TARGET_PER_CLASS = 150
MIN_SIZE = (512, 512)   # discard tiny images
TIMEOUT = 12            # seconds per image
BING_THREADS = 8
DDG_THREADS = 8

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
    # very dry / stressed lawn
    "dark_brown_yellow": [
        "lawn drought stressed brown grass",
        "yellow dry grass yard",
        "dead lawn patch"
    ],
    # mixed healthy + stressed
    "half_green_half_yellow": [
        "lawn partially yellow grass",
        "patchy lawn green and yellow",
        "uneven lawn color"
    ],
    # perfect lawn
    "perfect_health": [
        "healthy lush green lawn",
        "well maintained green grass yard",
        "golf course fairway lawn"
    ],
    # soggy ground
    "mushy_mud": [
        "muddy lawn with grass",
        "soggy muddy grass yard",
        "wet muddy turf"
    ],
    # leaks/bursts
    "gushing_water": [
        "sprinkler pipe burst gushing water yard",
        "underground water leak lawn",
        "sprinkler geyser leak"
    ],
    # for avoidance
    "people": [
        "people walking on lawn",
        "child running in yard",
        "person on grass yard"
    ],
}

# Common filters: photos only, color images. Bing supports filters dict.
BING_FILTERS = dict(
    type="photo",    # photo | clipart | line | animatedgif | transparent
    color="color",   # color | monochrome | blackandwhite
    size="large",    # small | medium | large | wallpaper
)

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def crawl_with_bing(save_dir: Path, queries, need, start_idx=0):
    if need <= 0:
        return 0
    crawler = BingImageCrawler(
        feeder_threads=1,
        parser_threads=2,
        downloader_threads=BING_THREADS,
        storage={"root_dir": str(save_dir)}
    )
    downloaded_total = 0
    for q in queries:
        remaining = need - downloaded_total
        if remaining <= 0:
            break
        try:
            crawler.crawl(
                keyword=q,
                max_num=remaining,
                # filters are "best-effort"—Bing sometimes ignores
                filters=BING_FILTERS,
                file_idx_offset=start_idx + downloaded_total
            )
            # no exact count returned; we’ll check filesystem
        except Exception as e:
            print(f"[BING] Error on '{q}': {e}")
        # throttle gently
        time.sleep(1.0)
        downloaded_total = count_valid_images(save_dir)  # conservative
        downloaded_total = min(downloaded_total, need)
    return downloaded_total

def crawl_with_ddg(save_dir: Path, queries, need, start_idx=0):
    if need <= 0:
        return 0
    crawler = DuckduckgoImageCrawler(
        feeder_threads=1,
        parser_threads=2,
        downloader_threads=DDG_THREADS,
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
                file_idx_offset=start_idx + (count_valid_images(save_dir) - downloaded_before),
                min_size=MIN_SIZE,
                timeout=TIMEOUT
            )
        except Exception as e:
            print(f"[DDG] Error on '{q}': {e}")
        time.sleep(0.5)
    downloaded_after = count_valid_images(save_dir)
    return downloaded_after - downloaded_before

def count_valid_images(folder: Path):
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    return sum(1 for p in folder.glob("*") if p.suffix.lower() in exts and p.stat().st_size > 10_000)

def main():
    ensure_dir(BASE_DIR)
    classes = list(CLASS_QUERIES.keys())

    for cls in classes:
        print(f"\n=== Class: {cls} (target {TARGET_PER_CLASS}) ===")
        out_dir = BASE_DIR / cls
        ensure_dir(out_dir)

        # Step 1: try Bing first
        have = count_valid_images(out_dir)
        print(f"Existing images: {have}")
        if have < TARGET_PER_CLASS:
            need = TARGET_PER_CLASS - have
            print(f"[BING] Attempting to fetch {need} images…")
            crawl_with_bing(out_dir, CLASS_QUERIES[cls], TARGET_PER_CLASS)

        # Step 2: top-up with DuckDuckGo
        have = count_valid_images(out_dir)
        if have < TARGET_PER_CLASS:
            need = TARGET_PER_CLASS - have
            print(f"[DDG] Topping up {need} images…")
            crawl_with_ddg(out_dir, CLASS_QUERIES[cls], need, start_idx=have)

        # Optional: quick pass to drop super-small files (icrawler already tries)
        # Recount
        have = count_valid_images(out_dir)
        print(f"Final count for {cls}: {have} files")

    print("\nAll done. Folders are in:", BASE_DIR)

if __name__ == "__main__":
    main()
