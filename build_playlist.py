#!/usr/bin/env python3

from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import re


# ============================================================
# PLAYLIST SOURCES
# ============================================================

SOURCES = [
    "https://iptv-org.github.io/iptv/countries/ae.m3u",
    "https://iptv-org.github.io/iptv/countries/sa.m3u",
    "https://iptv-org.github.io/iptv/countries/in.m3u",
    "https://iptv-org.github.io/iptv/regions/mena.m3u",
]


# ============================================================
# SETTINGS
# ============================================================

STREAM_TIMEOUT = 6
MAX_WORKERS = 15


# ============================================================
# MBC CHANNELS TO EXCLUDE
# ============================================================

BLOCKED_MBC = [
    "mbc 3",
    "mbc persia",
    "mbc loud",
    "mbc mood",
    "mbc fm",
]


# ============================================================
# UAE CHANNELS TO KEEP
# ============================================================

UAE_CHANNELS = [
    "dubai one",
    "sama dubai",
    "dubai tv",
]


# ============================================================
# INDIAN CHANNELS TO EXCLUDE
# ============================================================

BLOCKED_INDIAN_WORDS = [
    "news",
    "sports",
    "sport",
    "cricket",
]


# ============================================================
# DOWNLOAD PLAYLIST
# ============================================================

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


# ============================================================
# PARSE M3U
# ============================================================

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


# ============================================================
# GET CHANNEL NAME
# ============================================================

def channel_name(extinf):

    if "," not in extinf:
        return ""

    return extinf.rsplit(
        ",",
        1
    )[-1].strip()


# ============================================================
# NORMALIZE TEXT
# ============================================================

def normalize(text):

    return re.sub(
        r"[^a-z0-9]+",
        " ",
        text.lower()
    ).strip()


# ============================================================
# READ M3U ATTRIBUTE
# ============================================================

def get_attribute(extinf, attribute):

    match = re.search(
        rf'{re.escape(attribute)}="([^"]*)"',
        extinf,
        flags=re.IGNORECASE
    )

    if match:
        return match.group(1).strip()

    return ""


# ============================================================
# MBC FILTER
# ============================================================

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


# ============================================================
# UAE FILTER
# ============================================================

def is_uae_channel(name):

    n = normalize(name)

    return any(
        normalize(channel) in n
        for channel in UAE_CHANNELS
    )


# ============================================================
# INDIA FILTER
# ============================================================

def is_indian_channel(extinf, source):

    # Only channels from India's IPTV-org playlist
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

    # Remove news and sports
    for blocked in BLOCKED_INDIAN_WORDS:

        word = normalize(blocked)

        if (
            word in name
            or word in group
        ):
            return False

    return True


# ============================================================
# TEST STREAM
# ============================================================

def stream_works(url):

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
            timeout=STREAM_TIMEOUT
        ) as response:

            content_type = (
                response.headers
                .get("Content-Type", "")
                .lower()
            )

            data = response.read(8192)

        # Check for normal HLS playlist
        text = data.decode(
            "utf-8",
            errors="replace"
        )

        if "#EXTM3U" in text:
            return True

        # Some working streams use a video content type
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

    except (
        HTTPError,
        URLError,
        TimeoutError,
        Exception
    ):
        return False


# ============================================================
# TEST ONE CHANNEL
# ============================================================

def test_entry(entry):

    extinf, extras, url = entry

    name = channel_name(extinf)

    result = stream_works(url)

    return entry, name, result


# ============================================================
# MAIN
# ============================================================

def main():

    candidates = []
    seen_urls = set()

    print()
    print("==============================")
    print("Building CarTV Playlist")
    print("==============================")
    print()

    # --------------------------------------------------------
    # DOWNLOAD SOURCES
    # --------------------------------------------------------

    for source in SOURCES:

        print(f"Loading: {source}")

        try:

            text = fetch(source)

        except Exception as error:

            print(
                f"Could not load: {source}"
            )

            print(error)
            print()

            continue

        entries = parse_m3u(text)

        print(
            f"Found {len(entries)} entries"
        )

        # ----------------------------------------------------
        # FILTER CHANNELS
        # ----------------------------------------------------

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

            # Prevent duplicate stream URLs
            if url in seen_urls:
                continue

            seen_urls.add(url)

            candidates.append(entry)

        print()

    print("==============================")

    print(
        f"Found {len(candidates)} candidate streams"
    )

    print("==============================")
    print()

    # --------------------------------------------------------
    # TEST STREAMS IN PARALLEL
    # --------------------------------------------------------

    working = []

    print(
        f"Testing with {MAX_WORKERS} workers..."
    )

    print()

    with ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:

        futures = [
            executor.submit(
                test_entry,
                entry
            )
            for entry in candidates
        ]

        completed = 0

        for future in as_completed(futures):

            completed += 1

            try:

                entry, name, result = (
                    future.result()
                )

            except Exception as error:

                print(
                    f"[{completed}/{len(candidates)}] "
                    f"ERROR: {error}"
                )

                continue

            if result:

                print(
                    f"[{completed}/{len(candidates)}] "
                    f"WORKING: {name}"
                )

                working.append(entry)

            else:

                print(
                    f"[{completed}/{len(candidates)}] "
                    f"REMOVED: {name}"
                )

    # --------------------------------------------------------
    # SORT CHANNELS
    # --------------------------------------------------------

    working.sort(
        key=lambda entry: normalize(
            channel_name(entry[0])
        )
    )

    # --------------------------------------------------------
    # CREATE PLAYLIST
    # --------------------------------------------------------

    lines = [
        "#EXTM3U",
        "# CarTV Playlist",
        "# MBC + UAE + Indian Channels",
        "# Indian News and Sports Excluded",
    ]

    for extinf, extras, url in working:

        lines.append(extinf)

        lines.extend(extras)

        lines.append(url)

    Path(
        "playlist.m3u"
    ).write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8"
    )

    # --------------------------------------------------------
    # RESULTS
    # --------------------------------------------------------

    print()
    print("==============================")
    print("PLAYLIST CREATED")
    print("==============================")

    print(
        f"Candidate streams: "
        f"{len(candidates)}"
    )

    print(
        f"Working streams: "
        f"{len(working)}"
    )

    print(
        f"Removed streams: "
        f"{len(candidates) - len(working)}"
    )

    print()
    print("Channels in playlist:")
    print()

    for entry in working:

        print(
            "-",
            channel_name(entry[0])
        )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
