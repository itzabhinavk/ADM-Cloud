def human_filesize(num_bytes: int | None) -> str:
    size = float(num_bytes or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def human_datetime(value) -> str:
    if not value:
        return "—"
    return value.strftime("%d %b %Y, %H:%M")
