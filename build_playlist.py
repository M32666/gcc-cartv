#!/usr/bin/env python3

from urllib.request import Request, urlopen
from pathlib import Path
import re

SOURCES = [
    "https://iptv-org.github.io/iptv/countries/ae.m3u",
    "https://iptv-org.github.io/iptv/countries/sa.m3u",
    "https://iptv-org.github.io/iptv/countries/in.m3u",
    "https://iptv-org.github.io/iptv/regions/mena.m3u",
]

# MBC channels we do NOT want
BLOCKED_MBC = [
    "mbc 3",
    "mbc persia",
    "mbc loud",
    "mbc mood",
    "mbc fm",
]

# UAE channels to keep
UAE_CHANNELS = [
    "dubai one",
    "sama dubai",
    "dubai tv",
]

# Indian channels/categories we do NOT want
BLOCKED_INDIAN_WORDS = [
    "news",
    "sports",
    "sport",
    "cricket",
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
        return response.read().decode(
            "utf-8",
            errors="replace"
        )


def parse_m3u(text):
    lines = [
        line.strip()
        for line in text.splitlines()
    ]

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

    return extinf.rsplit(
        ",",
        1
    )[-1].strip()


def normalize(text):
    return re.sub(
        r"[^a-z0-9]+",
        " ",
        text.lower()
    ).strip()


def get_attribute(extinf, attribute):
    match = re.search(
        rf'{re.escape(attribute)}="([^"]*)"',
        extinf,
        flags=re.IGNORECASE
    )

    if match:
        return match.group(1).strip()

    return ""


def is_mbc(name):
    n = normalize(name)

    if not (
        n == "mbc"
        or n.startswith("mbc ")
    ):
        return False

    for blocked in BLOCKED_MBC:
        if normalize(blocked) in n:
            return False

    return True


def is_uae_channel(name):
    n = normalize(name)

    return any(
        normalize(channel) in n
        for channel in UAE_CHANNELS
    )


def is_indian_channel(extinf, source):
    # Only use this rule for IPTV-org's India playlist
    if "/countries/in.m3u" not in source:
        return False

    name = normalize(
        channel_name(extinf)
    )

    group = normalize(
        get_attribute(
            extinf,
            "group-title"
        )
    )

    # Remove Indian news and sports
    for blocked in BLOCKED_INDIAN_WORDS:

        word = normalize(blocked)

        if word in name or word in group:
            return False

    return True


def stream_works(url):
    """
    Test whether the stream URL responds.

    HLS playlists normally contain #EXTM3U.

    Some streams may respond using another content type,
    so we also check the HTTP response and content type.
    """

    try:
        req = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": (
                    "application/vnd.apple.mpegurl,"
                    "application/x-mpegURL,"
                    "video/*,"
                    "*/*"
                ),
            }
        )

        with urlopen(
            req,
            timeout=15
        ) as response:

            content_type = (
                response.headers
                .get("Content-Type", "")
                .lower()
            )

            data = response.read(8192)

        # Standard HLS playlist
        try:
            text = data.decode(
                "utf-8",
                errors="replace"
            )

            if "#EXTM3U" in text:
                return True

        except Exception:
            pass

        # Some servers identify the stream
        # through the HTTP content type
        valid_types = [
            "mpegurl",
            "video/",
            "application/octet-stream",
            "application/vnd.apple",
        ]

        if any(
            item in content_type
            for item in valid_types
        ):
            return True

        return False

    except Exception as error:
        print(f"FAILED: {url}")
        print(f"Reason: {error}")
        return False


def main():

    candidates = []
    seen_urls = set()

    print()
    print("==============================")
    print("Building CarTV playlist")
    print("==============================")
    print()

    for source in SOURCES:

        print(f"Loading: {source}")

        try:
            text = fetch(source)

        except Exception as error:
            print(f"Could not load: {source}")
            print(error)
            print()
            continue

        entries = parse_m3u(text)

        print(
            f"Found {len(entries)} entries"
        )

        for entry in entries:

            extinf, extras, url = entry
            name = channel_name(extinf)

            keep = (
                is_mbc(name)
                or is_uae_channel(name)
                or is_indian_channel(
                    extinf,
                    source
                )
            )

            if not keep:
                continue

            if url in seen_urls:
                continue

            seen_urls.add(url)
            candidates.append(entry)

        print()

    print("==============================")
    print(
        f"Testing {len(candidates)} candidate streams"
    )
    print("==============================")
    print()

    working = []

    for entry in candidates:

        extinf, extras, url = entry
        name = channel_name(extinf)

        print(f"Testing: {name}")

        if stream_works(url):
            print(f"WORKING: {name}")
            working.append(entry)

        else:
            print(f"REMOVED: {name}")

        print()

    # Sort channels alphabetically
    working.sort(
        key=lambda entry: normalize(
            channel_name(entry[0])
        )
    )

    lines = [
        "#EXTM3U",
        "# CarTV Playlist",
        "# MBC + UAE + Indian Entertainment",
        "# Indian News and Sports Excluded",
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
    print("PLAYLIST CREATED")
    print("==============================")
    print()

    print(
        f"Working channels: {len(working)}"
    )

    print()

    for entry in working:
        print(
            "-",
            channel_name(entry[0])
        )


if __name__ == "__main__":
    main()
