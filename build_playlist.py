#!/usr/bin/env python3
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import re
from pathlib import Path

SOURCES = {
    "gcc": "https://iptv-org.github.io/iptv/regions/gcc.m3u",
    "mena": "https://iptv-org.github.io/iptv/regions/mena.m3u",
    "india": "https://iptv-org.github.io/iptv/countries/in.m3u",
}

# Extra channels requested in addition to the complete GCC playlist.
# Entries are selected only when they exist in IPTV-org's public playlists.
WANTED = [
    "MBC Bollywood",
    "Zee Aflam",
    "Zee Aflam HD",
    "Zee Cinema",
    "Zee Alwan",
    "Abu Dhabi Sports 1",
    "Abu Dhabi Sports 2",
    "Abu Dhabi Sports 3",
    "Sharjah Sports",
    "Dubai Sports 1",
    "Dubai Sports 2",
    "Dubai Sports 3",
    "Dubai Racing 1",
    "Dubai Racing 2",
    "Dubai Racing 3",
    "Yas TV",
]

def fetch(url):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 gcc-cartv-playlist-builder"})
    with urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")

def parse_m3u(text):
    lines = [line.strip() for line in text.splitlines()]
    entries = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("#EXTINF:"):
            extinf = lines[i]
            extra = []
            j = i + 1
            while j < len(lines) and lines[j].startswith("#") and not lines[j].startswith("#EXTINF:"):
                extra.append(lines[j])
                j += 1
            if j < len(lines) and lines[j] and not lines[j].startswith("#"):
                url = lines[j]
                entries.append((extinf, extra, url))
                i = j
        i += 1
    return entries

def channel_name(extinf):
    if "," not in extinf:
        return ""
    return extinf.rsplit(",", 1)[-1].strip()

def normalized(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()

def main():
    gcc_text = fetch(SOURCES["gcc"])
    gcc_entries = parse_m3u(gcc_text)

    # Keep the full GCC playlist.
    output = list(gcc_entries)
    seen_urls = {e[2] for e in output}
    seen_names = {normalized(channel_name(e[0])) for e in output}

    # Search broader public playlists for requested extras.
    extra_pool = []
    for key in ("mena", "india"):
        try:
            extra_pool.extend(parse_m3u(fetch(SOURCES[key])))
        except Exception as exc:
            print(f"Warning: could not fetch {key}: {exc}")

    wanted_norm = {normalized(x): x for x in WANTED}
    found = set()

    for entry in extra_pool:
        name = channel_name(entry[0])
        n = normalized(name)
        if n in wanted_norm:
            found.add(wanted_norm[n])
            if entry[2] not in seen_urls:
                output.append(entry)
                seen_urls.add(entry[2])
                seen_names.add(n)

    header = [
        "#EXTM3U",
        "# GCC + selected public Bollywood/UAE Sports channels",
        "# Auto-built from IPTV-org public playlists.",
        "# Subscription-only beIN Sports feeds are intentionally not included.",
        "# If you have an authorized provider M3U, add those entries to custom_authorized.m3u.",
    ]

    # Optional user-supplied authorized entries.
    custom = Path("custom_authorized.m3u")
    custom_entries = []
    if custom.exists():
        custom_entries = parse_m3u(custom.read_text(encoding="utf-8", errors="replace"))
        for entry in custom_entries:
            if entry[2] not in seen_urls:
                output.append(entry)
                seen_urls.add(entry[2])

    lines = header[:]
    for extinf, extra, url in output:
        lines.append(extinf)
        lines.extend(extra)
        lines.append(url)

    Path("playlist.m3u").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {len(output)} channels to playlist.m3u")
    missing = [x for x in WANTED if x not in found and normalized(x) not in seen_names]
    if missing:
        print("Requested channels not found in compatible public IPTV-org playlists:")
        for name in missing:
            print(" -", name)

if __name__ == "__main__":
    main()
