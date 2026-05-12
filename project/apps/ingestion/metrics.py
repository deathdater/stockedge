from collections import Counter


INGESTION_COUNTERS = Counter()


def incr(metric: str, value: int = 1) -> None:
    INGESTION_COUNTERS[metric] += value
