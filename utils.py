import logging
import os
import re
from datetime import datetime, timedelta
from typing import List, Union


# Delayed import to avoid circular dependencies
def get_i18n():
    import i18n

    return i18n


DEFAULT_BD_YEAR = 1900

TDuration = int

TIME_MAP = {
    "minute": 1,
    "minutes": 1,
    "min": 1,
    "m": 1,
    "минута": 1,
    "минуты": 1,
    "минут": 1,
    "минуты": 1,
    "минут": 1,
    "минуты": 1,
    "минут": 1,
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
    "годы": 525600,
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


def validate_birthday_input(message: str, chat_id: int = None) -> tuple[bool, str]:
    lines = message.strip().split("\n")
    if len(lines) % 2 != 0:
        if chat_id is not None:
            i18n = get_i18n()
            error_msg = i18n.get_message("input_incomplete", chat_id)
        else:
            error_msg = (
                "It seems like your input is incomplete. "
                "Please ensure each name is followed by a date on a new line."
            )
        return False, error_msg

    for i in range(0, len(lines), 2):
        _ = lines[i].strip()  # name
        date_str = lines[i + 1].strip()

        success, parsed_date, has_year = parse_date(date_str)
        if not success:
            parts = date_str.split(".")
            if len(parts) == 3:
                try:
                    day, month, year = map(int, parts)
                    if year > datetime.now().year:
                        if chat_id is not None:
                            i18n = get_i18n()
                            error_msg = i18n.get_message(
                                "birthday_in_future", chat_id, date=date_str
                            )
                        else:
                            error_msg = (
                                f"Birthday '{date_str}' cannot be in the future. "
                                "Please provide a valid past date."
                            )
                        return False, error_msg
                except Exception:
                    pass
            if chat_id is not None:
                i18n = get_i18n()
                error_msg = i18n.get_message(
                    "date_parse_error", chat_id, date=date_str, line=i + 2
                )
            else:
                error_msg = (
                    f"I couldn't parse the date '{date_str}' on line {i + 2}. "
                    "Please use one of the following formats:\n"
                    "- day.month.year (e.g., 5.06.2001)\n"
                    "- day.month (e.g., 5.06)\n"
                    "- day.month age (e.g., 5.06 19)\n"
                    "Ensure the date is valid and within the last 200 years."
                )
            return False, error_msg

    return True, ""


def parse_date(date_str: str) -> tuple[bool, datetime | None, bool]:
    current_year = datetime.now().year
    date_parts = date_str.split()
    has_year = False

    try:
        if len(date_parts) == 1:  # day.month or day.month.year
            date_part = date_parts[0].split(".")
            if len(date_part) == 2:
                # Format: day.month, assume current year
                day, month = map(int, date_part)
                year = current_year
            elif len(date_part) == 3:
                # Format: day.month.year
                day, month, year = map(int, date_part)
                # Check if year is 2 digits
                if year < 200:
                    return False, None, False
                # Check if date is too far in the past (more than 200 years)
                if current_year - year > 200:
                    return False, None, False
                has_year = True
            else:
                return False, None, False
        elif len(date_parts) == 2:
            # Format: day.month age
            date_part, age_str = date_parts
            day, month = map(int, date_part.split("."))
            age = int(age_str)
            if age <= 0:
                return False, None, False

            if day != datetime.now().day and month != datetime.now().month:
                age += 1

            birth_year = current_year - age
            # Check if date is too far in the past (more than 200 years)
            if current_year - birth_year > 200:
                return False, None, False
            year = birth_year
            has_year = True
        else:
            return False, None, False

        parsed_date = datetime(year, month, day)
        if has_year and parsed_date > datetime.now():
            return False, None, False
        return True, parsed_date, has_year
    except ValueError:
        return False, None, False


def parse_dates(message: str) -> tuple[bool, list[tuple[str, datetime, bool]]]:
    lines = message.strip().split("\n")
    if len(lines) % 2 != 0:
        return False, []

    parsed_birthdays = []
    for i in range(0, len(lines), 2):
        name = lines[i].strip()
        date_str = lines[i + 1].strip()
        success, parsed_date, has_year = parse_date(date_str)
        if not success:
            return False, []
        parsed_birthdays.append((name, parsed_date, has_year))

    return True, parsed_birthdays


def log_exception(exc: Exception):
    """
    Helper function to log exception details with full traceback.
    """
    logging.error(f"An exception occurred: {exc}", exc_info=True)
    raise exc


def is_daytime():
    now = datetime.now()
    return now.hour >= 7 and now.hour <= 20


def cleanup_old_logs(log_dir=".", max_days=30):
    now = datetime.now()
    for filename in os.listdir(log_dir):
        if filename.startswith("bot.log."):
            filepath = os.path.join(log_dir, filename)
            file_modified = datetime.fromtimestamp(os.path.getmtime(filepath))
            if now - file_modified > timedelta(days=max_days):
                try:
                    os.remove(filepath)
                    logging.info(f"Deleted old log file: {filename}")
                except Exception as e:
                    logging.error(f"Failed to delete old log file {filename}: {e}")


def split_message(message: str, max_length: int = 4096) -> list[str]:
    """Splits a message into chunks of full lines, each within the specified maximum length."""
    lines = message.split("\n")
    chunks = []
    current_chunk = []

    for line in lines:
        if sum(len(chunk) + 1 for chunk in current_chunk) + len(line) + 1 > max_length:
            chunks.append("\n".join(current_chunk))
            current_chunk = []

        current_chunk.append(line)

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks
