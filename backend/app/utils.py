from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(UTC)


def normalize_utc(value: datetime) -> datetime:
    """Attach UTC to naive datetimes and convert aware datetimes to UTC."""
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
