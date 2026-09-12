#!/usr/bin/env python3

from urllib.request import Request, urlopen
from pathlib import Path
import re

SOURCES = [
    "https://iptv-org.github.io/iptv/countries/ae.m3u",
    "https://iptv-org.github.io/iptv/countries/sa.m3u",
    "https://iptv-org.github.io/iptv/regions/mena.m3u",
]

WANTED_UAE_SPORTS = [
    "abu dhabi sports",
    "ad sports",
    "dubai sports",
    "sharjah sports",
    "dubai racing",
    "yas tv",
]

BLOCKED_MBC = [
    "mbc 3",      # kids
    "mbc fm",     # music/radio-style channel
]

def fetch(url):
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )
    with urlopen(req, timeout=30) as response:
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
        for phrase in WANTED_UAE_SPORTS
    )


def is_mbc(name):
    n = normalize(name)

    if not (
        n == "mbc"
        or n.startswith("mbc ")
    ):
        return False

    if any(
        blocked in n
        for blocked in BLOCKED_MBC
    ):
        return False

    return True


def main():

    output = []
    seen_urls = set()

    for source in SOURCES:

        try:
            text = fetch(source)

        except Exception as error:
            print(
                f"Could not load {source}: {error}"
            )
            continue

        entries = parse_m3u(text)

        for entry in entries:

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

            output.append(entry)

    output.sort(
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
        "# UAE Sports + MBC",
    ]

    for extinf, extras, url in output:

        lines.append(extinf)

        lines.extend(extras)

        lines.append(url)

    Path("playlist.m3u").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8"
    )

    print(
        f"Created playlist with "
        f"{len(output)} channels"
    )

    print()

    print("Channels included:")

    for entry in output:
        print(
            "-",
            channel_name(entry[0])
        )


if __name__ == "__main__":
    main()
