import json
import requests
from pathlib import Path

SOURCES_FILE = "sources.json"
OUTPUT_FILE = "playlist.m3u"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def is_probable_html(text: str) -> bool:
    t = text.strip().lower()
    html_signs = [
        "<!doctype html",
        "<html",
        "<head",
        "<body",
        "<script",
        "<title"
    ]
    return any(sign in t for sign in html_signs)

def extract_items_from_response(source, response):
    fallback_name = source.get("fallback_name", "Unknown Channel")
    fallback_group = source.get("group", "Live")
    fallback_logo = source.get("logo", "")

    content_type = response.headers.get("Content-Type", "").lower()
    text = response.text.strip()

    items = []

    # JSON response
    if "application/json" in content_type:
        try:
            data = response.json()
        except Exception:
            return []

        if isinstance(data, dict):
            url = data.get("url") or data.get("stream_url") or data.get("src") or ""
            if url.startswith("http"):
                items.append({
                    "name": data.get("name", fallback_name),
                    "group": data.get("group", fallback_group),
                    "logo": data.get("logo", fallback_logo),
                    "url": url.strip()
                })

        elif isinstance(data, list):
            for entry in data:
                if not isinstance(entry, dict):
                    continue
                url = entry.get("url") or entry.get("stream_url") or entry.get("src") or ""
                if url.startswith("http"):
                    items.append({
                        "name": entry.get("name", fallback_name),
                        "group": entry.get("group", fallback_group),
                        "logo": entry.get("logo", fallback_logo),
                        "url": url.strip()
                    })

        return items

    # HTML হলে skip
    if is_probable_html(text):
        print(f"SKIP HTML PAGE: {response.url}")
        return []

    # Plain text direct URL হলে add
    if text.startswith("http://") or text.startswith("https://"):
        first_line = text.splitlines()[0].strip()
        if first_line.endswith(".m3u8") or ".m3u8?" in first_line:
            items.append({
                "name": fallback_name,
                "group": fallback_group,
                "logo": fallback_logo,
                "url": first_line
            })

    return items

def main():
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        sources = json.load(f)

    lines = ["#EXTM3U"]
    added = 0

    for source in sources:
        fetch_url = source.get("fetch_url", "").strip()
        if not fetch_url:
            continue

        try:
            r = requests.get(fetch_url, headers=HEADERS, timeout=20)
            r.raise_for_status()

            items = extract_items_from_response(source, r)

            if not items:
                print(f"NO DIRECT STREAM: {fetch_url}")
                continue

            for item in items:
                name = item["name"].replace('"', "'")
                group = item["group"].replace('"', "'")
                logo = item["logo"].replace('"', "'")
                url = item["url"].strip()

                lines.append(
                    f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" group-title="{group}",{name}'
                )
                lines.append(url)
                added += 1

            print(f"OK: {fetch_url} -> {len(items)} item(s)")

        except Exception as e:
            print(f"ERROR: {fetch_url} -> {e}")

    Path(OUTPUT_FILE).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Done. {added} channel(s) written.")

if __name__ == "__main__":
    main()