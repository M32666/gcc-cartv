#!/usr/bin/env python3
from urllib.request import Request, urlopen
from pathlib import Path
import re

SOURCES = [
    "https://iptv-org.github.io/iptv/countries/ae.m3u",
    "https://iptv-org.github.io/iptv/regions/mena.m3u",
]

UAE_SPORTS = {
    "abu dhabi sports 1",
    "abu dhabi sports 2",
    "abu dhabi sports 3",
    "ad sports 1",
    "ad sports 2",
    "ad sports 3",
    "dubai sports 1",
    "dubai sports 2",
    "dubai sports 3",
    "sharjah sports",
    "dubai racing 1",
    "dubai racing 2",
    "dubai racing 3",
    "yas tv",
}

def fetch(url):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")

def parse_m3u(text):
    lines = [x.strip() for x in text.splitlines()]
    out = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("#EXTINF:"):
            extinf = lines[i]
            extras = []
            j = i + 1
            while j < len(lines) and lines[j].startswith("#") and not lines[j].startswith("#EXTINF:"):
                extras.append(lines[j])
                j += 1
            if j < len(lines) and lines[j] and not lines[j].startswith("#"):
                out.append((extinf, extras, lines[j]))
                i = j
        i += 1
    return out

def name_of(extinf):
    return extinf.rsplit(",", 1)[-1].strip() if "," in extinf else ""

def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()

def is_mbc(name):
    n = norm(name)
    return n == "mbc" or n.startswith("mbc ")

def is_uae_sport(name):
    n = norm(name)
    if n in UAE_SPORTS:
        return True
    # Catch common naming variants while keeping only UAE sports/racing.
    return any(k in n for k in (
        "abu dhabi sports",
        "ad sports",
        "dubai sports",
        "sharjah sports",
        "dubai racing",
        "yas tv",
    ))

def main():
    entries = []
    seen = set()

    for src in SOURCES:
        for entry in parse_m3u(fetch(src)):
            name = name_of(entry[0])
            if not (is_mbc(name) or is_uae_sport(name)):
                continue
            if entry[2] in seen:
                continue
            seen.add(entry[2])
            entries.append(entry)

    # Keep UAE sports first, then MBC channels alphabetically.
    entries.sort(key=lambda e: (0 if is_uae_sport(name_of(e[0])) else 1, norm(name_of(e[0]))))

    lines = [
        "#EXTM3U",
        "# UAE Sports + MBC only",
        "# Public streams sourced from IPTV-org.",
        "# No general news, kids, or unrelated entertainment channels.",
    ]

    for extinf, extras, url in entries:
        lines.append(extinf)
        lines.extend(extras)
        lines.append(url)

    Path("playlist.m3u").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(entries)} channels")

if __name__ == "__main__":
    main()
