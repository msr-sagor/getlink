import json
import requests
from pathlib import Path

SOURCES_FILE = "sources.json"
OUTPUT_FILE = "playlist.m3u"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def get_response_data(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()

    content_type = r.headers.get("Content-Type", "").lower()

    if "application/json" in content_type:
        return r.json()

    text = r.text.strip()

    # যদি text JSON-like হয়
    if text.startswith("{") or text.startswith("["):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    # নাহলে plain text হিসেবে return
    return text

def normalize_items(source, data):
    fallback_name = source.get("fallback_name", "Unknown Channel")
    fallback_group = source.get("group", "Live")
    fallback_logo = source.get("logo", "")

    items = []

    # Case 1: plain text direct URL
    if isinstance(data, str):
        url = data.strip()
        if url:
            items.append({
                "name": fallback_name,
                "group": fallback_group,
                "logo": fallback_logo,
                "url": url
            })

    # Case 2: JSON object
    elif isinstance(data, dict):
        url = data.get("url") or data.get("stream_url") or data.get("src") or ""
        name = data.get("name") or data.get("title") or fallback_name
        group = data.get("group") or data.get("category") or fallback_group
        logo = data.get("logo") or data.get("image") or fallback_logo

        if url:
            items.append({
                "name": name,
                "group": group,
                "logo": logo,
                "url": url.strip()
            })

    # Case 3: JSON list
    elif isinstance(data, list):
        for entry in data:
            if not isinstance(entry, dict):
                continue

            url = entry.get("url") or entry.get("stream_url") or entry.get("src") or ""
            name = entry.get("name") or entry.get("title") or fallback_name
            group = entry.get("group") or entry.get("category") or fallback_group
            logo = entry.get("logo") or entry.get("image") or fallback_logo

            if url:
                items.append({
                    "name": name,
                    "group": group,
                    "logo": logo,
                    "url": url.strip()
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
            data = get_response_data(fetch_url)
            items = normalize_items(source, data)

            for item in items:
                name = item["name"].replace('"', "'")
                group = item["group"].replace('"', "'")
                logo = item["logo"].replace('"', "'")
                url = item["url"]

                lines.append(
                    f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" group-title="{group}",{name}'
                )
                lines.append(url)
                added += 1

            print(f"OK: {fetch_url} -> {len(items)} item(s)")

        except Exception as e:
            print(f"ERROR: {fetch_url} -> {e}")

    Path(OUTPUT_FILE).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Done. {added} channel(s) written to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
