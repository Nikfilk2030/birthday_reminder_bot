import re
from typing import List, Union

TDuration = int

TIME_MAP = {
    "minute": 1,
    "minutes": 1,
    "min": 1,
    "m": 1,
    "час": 60,
    "часы": 60,
    "часов": 60,
    "hour": 60,
    "hours": 60,
    "h": 60,
    "день": 1440,
    "дня": 1440,
    "дней": 1440,
    "day": 1440,
    "days": 1440,
    "d": 1440,
    "месяц": 43200,
    "месяца": 43200,
    "месяцев": 43200,
    "month": 43200,
    "months": 43200,
    "год": 525600,
    "года": 525600,
    "годов": 525600,
    "year": 525600,
    "years": 525600,
    "y": 525600,
}


def get_possible_time_formats() -> List[str]:
    return list(TIME_MAP.keys())


def is_timestamp_valid(timestamp_str: str) -> bool:
    normalized_str = re.sub(r"\s+", "", timestamp_str.lower())

    match = re.match(r"^(\d+)(\D+)$", normalized_str)
    if match:
        _, unit = match.groups()
        return unit in TIME_MAP
    return False


def get_time(timestamp_str: str) -> Union[TDuration, None]:
    normalized_str = re.sub(r"\s+", "", timestamp_str.lower())

    match = re.match(r"^(\d+)(\D+)$", normalized_str)
    if not match:
        return None

    amount_str, unit = match.groups()

    if unit in TIME_MAP:
        amount = int(amount_str)
        return amount * TIME_MAP[unit]

    return None
