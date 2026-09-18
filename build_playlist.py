BLOCKED_INDIAN_CATEGORIES = [
    "news",
    "sports",
]

def get_attribute(extinf, attribute):
    match = re.search(
        rf'{re.escape(attribute)}="([^"]*)"',
        extinf,
        flags=re.IGNORECASE
    )
    return match.group(1).strip() if match else ""


def is_indian_channel(extinf, source):
    # Only treat entries from the India playlist as Indian channels
    if "/countries/in.m3u" not in source:
        return False

    group = normalize(get_attribute(extinf, "group-title"))
    name = normalize(channel_name(extinf))

    # Remove news and sports
    blocked_words = [
        "news",
        "sports",
        "sport",
        "cricket",
    ]

    for word in blocked_words:
        if word in group or word in name:
            return False

    return True
