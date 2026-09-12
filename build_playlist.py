#!/usr/bin/env python3

from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from pathlib import Path
import re

SOURCES = [
    "https://iptv-org.github.io/iptv/countries/ae.m3u",
    "https://iptv-org.github.io/iptv/countries/sa.m3u",
    "https://iptv-org.github.io/iptv/regions/mena.m3u",
]

UAE_SPORTS = [
    "abu dhabi sports",
    "ad sports",
    "dubai sports",
    "sharjah sports",
    "dubai racing",
    "yas tv",
]

BLOCKED_MBC = [
    "mbc 3",
    "mbc persia",
    "mbc loud",
    "mbc mood",
    "mbc fm",
]

def fetch(url, timeout=20):
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "*/*",
        }
    )

    with urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_m3u(text):
    lines = [line.strip() for line in text.splitlines()]
    entries = []

    i = 0

    while i < len(lines):
        if lines[i].startswith("#EXTINF:"):
            extinf = lines[i]
            extras = []

            j = i + 1

            while (
                j < len(lines)
                and lines[j].startswith("#")
                and not lines[j].startswith("#EXTINF:")
            ):
                extras.append(lines[j])
                j += 1

            if (
                j < len(lines)
                and lines[j]
                and not lines[j].startswith("#")
            ):
                entries.append(
                    (
                        extinf,
                        extras,
                        lines[j]
                    )
                )

                i = j

        i += 1

    return entries


def channel_name(extinf):
    if "," not in extinf:
        return ""

    return extinf.rsplit(",", 1)[-1].strip()


def normalize(text):
    return re.sub(
        r"[^a-z0-9]+",
        " ",
        text.lower()
    ).strip()


def is_uae_sport(name):
    n = normalize(name)

    return any(
        phrase in n
        for phrase in UAE_SPORTS
    )


def is_mbc(name):
    n = normalize(name)

    if not (
        n == "mbc"
        or n.startswith("mbc ")
    ):
        return False

    for blocked in BLOCKED_MBC:
        if blocked in n:
            return False

    return True


def stream_works(url):
    try:
        req = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/vnd.apple.mpegurl,application/x-mpegURL,*/*",
            }
        )

        with urlopen(req, timeout=15) as response:
            data = response.read(8192).decode(
                "utf-8",
                errors="replace"
            )

        return "#EXTM3U" in data

    except (HTTPError, URLError, TimeoutError, Exception) as error:
        print(
            f"FAILED: {url}"
        )
        print(
            f"Reason: {error}"
        )
        return False


def main():
    candidates = []
    seen_urls = set()

    for source in SOURCES:

        try:
            text = fetch(source)

        except Exception as error:
            print(
                f"Could not load source: {source}"
            )
            print(
                f"Reason: {error}"
            )
            continue

        for entry in parse_m3u(text):

            extinf, extras, url = entry

            name = channel_name(extinf)

            if not (
                is_uae_sport(name)
                or is_mbc(name)
            ):
                continue

            if url in seen_urls:
                continue

            seen_urls.add(url)

            candidates.append(entry)

    working = []

    print()
    print("Testing streams...")
    print()

    for entry in candidates:

        extinf, extras, url = entry

        name = channel_name(extinf)

        print(
            f"Testing: {name}"
        )

        if stream_works(url):
            print(
                f"WORKING: {name}"
            )

            working.append(entry)

        else:
            print(
                f"REMOVED: {name}"
            )

        print()

    working.sort(
        key=lambda entry: (
            0
            if is_uae_sport(
                channel_name(entry[0])
            )
            else 1,
            normalize(
                channel_name(entry[0])
            )
        )
    )

    lines = [
        "#EXTM3U",
        "# UAE Sports + selected working MBC channels",
    ]

    for extinf, extras, url in working:

        lines.append(extinf)

        lines.extend(extras)

        lines.append(url)

    Path("playlist.m3u").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8"
    )

    print()
    print("==============================")
    print(
        f"Created playlist with {len(working)} working channels"
    )
    print("==============================")
    print()

    for entry in working:
        print(
            "-",
            channel_name(entry[0])
        )


if __name__ == "__main__":
    main()
