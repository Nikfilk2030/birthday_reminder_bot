import enum
import logging
import os
import threading
import time
from collections import defaultdict
from datetime import datetime

import telebot
from dotenv import load_dotenv
from telebot import apihelper
from telebot.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                           ReplyKeyboardRemove)

import db
import i18n
import utils

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s [%(filename)s:%(lineno)d]",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler(),
    ],
)

load_dotenv()

# Check if prestable mode is enabled
PRESTABLE_MODE = os.getenv("PRESTABLE_MODE", "false").lower() == "true"

if PRESTABLE_MODE:
    TOKEN = os.getenv("PRESTABLE_TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        logging.critical("PRESTABLE_TELEGRAM_BOT_TOKEN is not set in the .env file!")
        raise ValueError("PRESTABLE_TELEGRAM_BOT_TOKEN is not set in the .env file!")
    logging.info("🧪 Running in PRESTABLE mode")
else:
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        logging.critical("TELEGRAM_BOT_TOKEN is not set in the .env file!")
        raise ValueError("TELEGRAM_BOT_TOKEN is not set in the .env file!")
    logging.info("🚀 Running in PRODUCTION mode")

bot = telebot.TeleBot(TOKEN)

user_states = {}

# Global dictionary to track messages related to birthday registration
birthday_registration_messages = defaultdict(list)
# Global dictionary to track messages related to birthday deletion
birthday_deletion_messages = defaultdict(list)
# Global dictionary to track messages related to backup registration
register_backup_messages = defaultdict(list)

REMINDED_DAYS = [0, 1, 3, 7]


class TUserState(enum.Enum):
    Default = "default"
    AwaitingInterval = "awaiting_interval"
    AwaitingDeletion = "awaiting_deletion"
    AwaitingBirthday = "awaiting_birthday"


class TCommand(enum.Enum):
    Start = "start"
    Backup = "backup"
    RegisterBirthday = "register_birthday"
    RegisterBackup = "register_backup"
    UnregisterBackup = "unregister_backup"
    DeleteBirthday = "delete_birthday"
    Stats = "stats"
    Share = "share"
    Language = "language"


# Command mappings for text commands
COMMAND_MAPPINGS = {
    "/start": TCommand.Start,
    "/help": TCommand.Start,
    "/backup": TCommand.Backup,
    "/register_birthday": TCommand.RegisterBirthday,
    "/register_backup": TCommand.RegisterBackup,
    "/unregister_backup": TCommand.UnregisterBackup,
    "/delete_birthday": TCommand.DeleteBirthday,
    "/share": TCommand.Share,
    "/stats": TCommand.Stats,
}


def get_button_to_command_mapping(chat_id: int) -> dict:
    """Get button text to command mapping for specific user's language"""
    return {
        i18n.get_button_text("start", chat_id): TCommand.Start,
        i18n.get_button_text("backup", chat_id): TCommand.Backup,
        i18n.get_button_text("register_birthday", chat_id): TCommand.RegisterBirthday,
        i18n.get_button_text("register_backup", chat_id): TCommand.RegisterBackup,
        i18n.get_button_text("unregister_backup", chat_id): TCommand.UnregisterBackup,
        i18n.get_button_text("delete_birthday", chat_id): TCommand.DeleteBirthday,
        i18n.get_button_text("share", chat_id): TCommand.Share,
        i18n.get_button_text("stats", chat_id): TCommand.Stats,
        i18n.get_button_text("language", chat_id): TCommand.Language,
    }


def get_command_descriptions(chat_id: int) -> dict:
    """Get command descriptions for specific user's language"""
    return {
        i18n.get_button_text("start", chat_id): i18n.get_button_description(
            "start", chat_id
        ),
        i18n.get_button_text("register_birthday", chat_id): i18n.get_button_description(
            "register_birthday", chat_id
        ),
        i18n.get_button_text("delete_birthday", chat_id): i18n.get_button_description(
            "delete_birthday", chat_id
        ),
        i18n.get_button_text("backup", chat_id): i18n.get_button_description(
            "backup", chat_id
        ),
        i18n.get_button_text("register_backup", chat_id): i18n.get_button_description(
            "register_backup", chat_id
        ),
        i18n.get_button_text("unregister_backup", chat_id): i18n.get_button_description(
            "unregister_backup", chat_id
        ),
        i18n.get_button_text("share", chat_id): i18n.get_button_description(
            "share", chat_id
        ),
        i18n.get_button_text("stats", chat_id): i18n.get_button_description(
            "stats", chat_id
        ),
    }


def get_all_birthdays(chat_id: int, need_id: bool = False) -> str:
    return "\n".join(db.get_all_birthdays(chat_id, need_id))


def is_group_chat(message) -> bool:
    return message.chat.type in ["group", "supergroup"]


def remove_keyboard(message):
    delete_message = bot.send_message(
        message.chat.id,
        i18n.get_message("keyboard_removed", message.chat.id),
        reply_markup=ReplyKeyboardRemove(),
    )
    bot.delete_message(delete_message.chat.id, delete_message.message_id)


def get_reply_markup(message) -> InlineKeyboardMarkup | None:
    chat_id = message.chat.id
    markup = InlineKeyboardMarkup()
    buttons = [
        InlineKeyboardButton(
            i18n.get_button_text("start", chat_id), callback_data="start"
        ),
        InlineKeyboardButton(
            i18n.get_button_text("backup", chat_id), callback_data="backup"
        ),
        InlineKeyboardButton(
            i18n.get_button_text("register_birthday", chat_id),
            callback_data="register_birthday",
        ),
        InlineKeyboardButton(
            i18n.get_button_text("register_backup", chat_id),
            callback_data="register_backup",
        ),
        InlineKeyboardButton(
            i18n.get_button_text("delete_birthday", chat_id),
            callback_data="delete_birthday",
        ),
        InlineKeyboardButton(
            i18n.get_button_text("unregister_backup", chat_id),
            callback_data="unregister_backup",
        ),
        InlineKeyboardButton(
            i18n.get_button_text("share", chat_id), callback_data="share"
        ),
        InlineKeyboardButton(
            i18n.get_button_text("stats", chat_id), callback_data="stats"
        ),
        InlineKeyboardButton(
            i18n.get_button_text("language", chat_id), callback_data="language"
        ),
    ]
    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i : (i + 2)])
    return markup


def get_language_keyboard() -> InlineKeyboardMarkup:
    """Create language selection keyboard"""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
        InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
    )
    return markup


def get_reminder_settings_keyboard(chat_id) -> InlineKeyboardMarkup:
    current_settings = db.get_reminder_settings(chat_id) or []

    markup = InlineKeyboardMarkup()

    reminder_buttons = [
        InlineKeyboardButton(
            f"{'✅' if days in current_settings else '❌'} {days} {i18n.get_message('days', chat_id)}",
            callback_data=f"reminder_{days}",
        )
        for days in REMINDED_DAYS
    ]

    markup.row(reminder_buttons[0], reminder_buttons[1])
    markup.row(reminder_buttons[2], reminder_buttons[3])

    return markup


def handle_stats(message):
    chat_id = message.chat.id

    # Retrieve pre-formatted birthday strings used for display.
    local_birthdays = db.get_all_birthdays(chat_id)
    global_birthdays = db.get_all_birthdays_for_all_chats()

    total_birthdays_for_this_chat = len(local_birthdays)
    total_birthdays_for_all_chats = len(global_birthdays)
    total_users = len(set(chat_id for chat_id, in db.get_all_chat_ids()))

    # Calculate birthdays in the current month for the local chat.
    current_month = datetime.now().month
    birthdays_this_month = []
    for birthday in local_birthdays:
        date_str = birthday.split(", ")[0]
        try:
            date = datetime.strptime(date_str, "%d %B %Y")
        except ValueError:
            date = datetime.strptime(date_str, "%d %B")

        if date.month == current_month:
            birthdays_this_month.append(birthday)
    total_birthdays_this_month = len(birthdays_this_month)

    # Helper function to extract the month name from a birthday string.
    def extract_month(birthday_line: str) -> str:
        try:
            date_part = birthday_line.split(",")[0].strip()
            tokens = date_part.split(" ")
            if len(tokens) >= 2:
                return tokens[1]
            return ""
        except Exception:
            return ""

    # Calculate the most popular birthday month locally.
    local_month_counts = {}
    for birthday in local_birthdays:
        month = extract_month(birthday)
        if month:
            local_month_counts[month] = local_month_counts.get(month, 0) + 1

    if local_month_counts:
        local_most_popular_month, local_count = max(
            local_month_counts.items(), key=lambda x: x[1]
        )
    else:
        local_most_popular_month, local_count = "N/A", 0

    # Calculate the most popular birthday month globally.
    global_month_counts = {}
    for birthday in global_birthdays:
        month = extract_month(birthday)
        if month:
            global_month_counts[month] = global_month_counts.get(month, 0) + 1

    # Calculate most popular birthday month globally.
    global_month_counts = {}
    for birthday in global_birthdays:
        month = extract_month(birthday)
        if month:
            global_month_counts[month] = global_month_counts.get(month, 0) + 1

    if global_month_counts:
        global_most_popular_month, global_count = max(
            global_month_counts.items(), key=lambda x: x[1]
        )
    else:
        global_most_popular_month, global_count = "N/A", 0

    # Compute Age Statistics using the already given birthday strings.
    # Only birthdays with a full_date (i.e. %d %B %Y format) are considered.
    def compute_age_metrics(birthday_strings: list[str]):
        ages = []
        now = datetime.now()
        current_year = now.year
        for birthday in birthday_strings:
            if not birthday or not isinstance(birthday, str):
                continue
            try:
                # Extract the date part safely
                parts = birthday.split(",", 1)
                if not parts:
                    continue
                date_str = parts[0].strip()

                # Will work only if the date contains a full year
                date_dt = datetime.strptime(date_str, "%d %B %Y")

                # Compute age and adjust if birthday hasn't taken place yet this year
                birthday_this_year = date_dt.replace(year=current_year)
                age = current_year - date_dt.year
                if now < birthday_this_year:
                    age -= 1
                ages.append(age)
            except (ValueError, IndexError):
                continue  # Skip birthdays with errors

        if ages:
            avg_age = sum(ages) / len(ages)
            min_age = min(ages)
            max_age = max(ages)
            return avg_age, min_age, max_age
        return None, None, None

    avg_age_local, min_age_local, max_age_local = compute_age_metrics(local_birthdays)
    avg_age_global, min_age_global, max_age_global = compute_age_metrics(
        global_birthdays
    )

    if avg_age_local is not None:
        local_age_stats = (
            f"• Age Statistics:\n"
            f"   - Average Age: {avg_age_local:.1f}\n"
            f"   - Minimum Age: {min_age_local}\n"
            f"   - Maximum Age: {max_age_local}\n"
        )
    else:
        local_age_stats = "• Age Statistics: N/A (no birthdays with full date)\n"

    if avg_age_global is not None:
        global_age_stats = (
            f"• Age Statistics:\n"
            f"   - Average Age: {avg_age_global:.1f}\n"
            f"   - Minimum Age: {min_age_global}\n"
            f"   - Maximum Age: {max_age_global}\n"
        )
    else:
        global_age_stats = "• Age Statistics: N/A (no birthdays with full date)\n"

    # Assemble the local statistics.
    local_stats = (
        "📍 *Local Statistics:*\n\n"
        f"• Total Birthdays in this Chat: {total_birthdays_for_this_chat}\n"
        f"• Birthdays in this Month: {total_birthdays_this_month}\n"
        f"• Most Popular Birthday Month: {local_most_popular_month} ({local_count} birthdays)\n"
        f"{local_age_stats}"
    )

    # Assemble the global statistics.
    global_stats = (
        "🌐 *Global Statistics:*\n\n"
        f"• Total Birthdays in All Chats: {total_birthdays_for_all_chats}\n"
        f"• Total Users: {total_users}\n"
        f"• Most Popular Birthday Month: {global_most_popular_month} ({global_count} birthdays)\n"
        f"{global_age_stats}"
    )

    stats_message = f"{local_stats}\n{global_stats}"

    bot.send_message(
        chat_id,
        stats_message,
        parse_mode="Markdown",
    )

    user_states[chat_id] = TUserState.Default


def handle_start(message):
    chat_id = message.chat.id
    user_states[chat_id] = TUserState.Default

    # remove /start command itself
    bot.delete_message(chat_id, message.message_id)

    # Remove any existing keyboard
    remove_keyboard(message)

    backup_ping_settings = db.select_from_backup_ping(chat_id)
    if backup_ping_settings.is_active:
        backup_ping_msg = (
            i18n.get_message(
                "backup_ping_active",
                chat_id,
                interval=backup_ping_settings.update_timedelta,
            )
            + "\n"
        )
    else:
        backup_ping_msg = i18n.get_message("backup_ping_inactive", chat_id) + "\n"

    commands_descriptions = get_command_descriptions(chat_id)
    commands_msg = "\n".join(
        [
            f"{command}: {description}"
            for command, description in commands_descriptions.items()
        ]
    )

    welcome_message = f"""
{i18n.get_message("welcome_title", chat_id)}

{i18n.get_message("welcome_subtitle", chat_id)}

{i18n.get_message("what_can_bot_do", chat_id)}
{i18n.get_message("bot_features", chat_id)}

{i18n.get_message("how_to_use", chat_id)}
{i18n.get_message("how_to_use_steps", chat_id)}

{i18n.get_message("available_commands", chat_id)}
{commands_msg}

{backup_ping_msg}
{i18n.get_message("contribute", chat_id)}
"""

    bot.send_message(
        chat_id,
        welcome_message,
        reply_markup=get_reply_markup(message),
        parse_mode="Markdown",
    )
    logging.debug(f"Sent welcome message to Chat ID {chat_id}")

    bot.send_message(
        chat_id,
        f"{i18n.get_message('configure_reminders', chat_id)}\n\n{i18n.get_message('reminder_example', chat_id)}",
        reply_markup=get_reminder_settings_keyboard(chat_id),
        parse_mode="Markdown",
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("reminder_"))
def handle_reminder_callback(call):
    days = int(call.data.split("_")[1])
    chat_id = call.message.chat.id

    current_settings = db.get_reminder_settings(chat_id) or []

    if days in current_settings:
        current_settings.remove(days)
    else:
        current_settings.append(days)

    db.update_reminder_settings(chat_id, current_settings)

    bot.edit_message_reply_markup(
        chat_id=chat_id,
        message_id=call.message.message_id,
        reply_markup=get_reminder_settings_keyboard(chat_id),
    )

    status = i18n.get_message(
        "reminder_enabled" if days in current_settings else "reminder_disabled", chat_id
    )
    bot.answer_callback_query(
        call.id,
        f"{status} {days}{i18n.get_message('reminder_days_suffix', chat_id)}",
    )

    user_states[call.message.chat.id] = TUserState.Default


@bot.callback_query_handler(func=lambda call: call.data.startswith("lang_"))
def handle_language_callback(call):
    language_code = call.data.split("_")[1]
    chat_id = call.message.chat.id

    if i18n.set_user_language(chat_id, language_code):
        # Send confirmation message
        bot.send_message(
            chat_id,
            i18n.get_message("language_changed", chat_id),
            parse_mode="Markdown",
        )

        # Refresh the main menu with new language
        handle_start(call.message)

    bot.answer_callback_query(call.id)


def get_all_birthdays_formatted(chat_id: int, need_id: bool = False) -> str:
    all_birthdays = get_all_birthdays(chat_id, need_id)

    if not all_birthdays:
        return i18n.get_message("no_birthdays", chat_id)

    birthdays_by_month = {}
    for line in all_birthdays.split("\n"):
        date_str, name, *rest = line.split(", ")
        date = datetime.strptime(
            date_str, "%d %B %Y" if "Current age" in line else "%d %B"
        )
        month = date.strftime("%B")
        # Translate month name
        translated_month = i18n.get_month_name(month, chat_id)
        if translated_month not in birthdays_by_month:
            birthdays_by_month[translated_month] = []
        birthdays_by_month[translated_month].append(line)

    markdown_message = f"{i18n.get_message('your_birthdays', chat_id)}\n\n"
    for month, birthdays in birthdays_by_month.items():
        markdown_message += f"*{month}*\n"
        for birthday in birthdays:
            markdown_message += f"- {birthday}\n"
        markdown_message += "\n"

    user_states[chat_id] = TUserState.Default

    return markdown_message


def get_all_birthdays_for_share(chat_id: int) -> str:
    all_birthdays = get_all_birthdays(chat_id)

    if not all_birthdays:
        return "Nothing found"

    formatted_birthdays = []
    for line in all_birthdays.split("\n"):
        date_str, name, *rest = line.split(", ")
        date = datetime.strptime(
            date_str, "%d %B %Y" if "Current age" in line else "%d %B"
        )
        if date.year != utils.DEFAULT_BD_YEAR:
            formatted_date = date.strftime("%d.%m.%Y")
        else:
            formatted_date = date.strftime("%d.%m")
        formatted_birthdays.append(name)
        formatted_birthdays.append(formatted_date)

    return "\n".join(formatted_birthdays)


def send_backup(message):
    all_birthdays = get_all_birthdays_formatted(message.chat.id)
    birthdays_messages = utils.split_message(all_birthdays)

    for birthday_message in birthdays_messages:
        bot.send_message(
            message.chat.id,
            birthday_message,
            parse_mode="Markdown",
        )

    user_states[message.chat.id] = TUserState.Default


def process_birthday_pings():
    last_reset_date = None
    while True:
        minutes = 5
        time.sleep(minutes * 60)

        if not utils.is_daytime():
            continue

        try:
            # Reset reminder flags once per day at midnight
            current_date = datetime.now().date()
            if last_reset_date != current_date:
                db.reset_birthday_reminder_flags()
                last_reset_date = current_date
                logging.info("Daily reset of birthday reminder flags completed")

            for days in REMINDED_DAYS:
                upcoming_birthdays = db.get_upcoming_birthdays(days)

                for id, chat_id, name, birthday_str, has_year in upcoming_birthdays:
                    user_settings = db.get_reminder_settings(chat_id)
                    if not user_settings:
                        continue

                    birthday = datetime.strptime(birthday_str, "%Y-%m-%d")
                    current_year = datetime.now().year
                    birthday_this_year = birthday.replace(year=current_year)

                    today = datetime.now().replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                    days_until = (birthday_this_year - today).days

                    # Only send reminder if user has enabled this day.
                    if days_until in user_settings:
                        try:
                            age_text = ""
                            if has_year:
                                age = current_year - birthday.year
                                age_text = i18n.get_message(
                                    "age_suffix", chat_id, age=age
                                )

                            if days_until == 0:
                                bot.send_message(chat_id, "🎂")
                                reminder_text = i18n.get_message(
                                    "today_birthday",
                                    chat_id,
                                    name=name,
                                    age_text=age_text,
                                )
                            else:
                                reminder_text = i18n.get_message(
                                    "upcoming_birthday",
                                    chat_id,
                                    days=days_until,
                                    name=name,
                                    age_text=age_text,
                                )

                            bot.send_message(chat_id, reminder_text)
                            db.mark_birthday_reminder_sent(id, days_until)
                        except telebot.apihelper.ApiTelegramException as e:
                            if e.error_code == 403:  # Bot was blocked by the user
                                logging.warning(
                                    f"Bot was blocked by user {chat_id}, skipping notifications"
                                )
                                # Mark reminder as sent to avoid retrying
                                db.mark_birthday_reminder_sent(id, days_until)
                            else:
                                raise  # Re-raise other API exceptions

        except Exception as e:
            logging.error(f"Error during birthday ping processing: {e}")
            utils.log_exception(e)


def send_share_message(message):
    all_birthdays = get_all_birthdays_for_share(message.chat.id)
    birthdays_messages = utils.split_message(all_birthdays)

    for birthday_message in birthdays_messages:
        bot.send_message(message.chat.id, birthday_message, parse_mode="Markdown")


def register_birthday(message):
    chat_id = message.chat.id

    instruct_msg = bot.send_message(
        chat_id,
        i18n.get_message("register_birthday_instructions", chat_id),
        parse_mode="Markdown",
    )

    birthday_registration_messages[chat_id] = set([instruct_msg.message_id])
    user_states[chat_id] = TUserState.AwaitingBirthday


def process_backup_pings():
    while True:
        minutes = 5
        time.sleep(minutes * 60)
        try:
            all_chat_ids = db.get_all_chat_ids()
            if all_chat_ids is None:
                logging.error("Failed to retrieve chat IDs")
                continue

            for chat_id in all_chat_ids:
                chat_id = chat_id[0]

                backup_ping_settings = db.select_from_backup_ping(chat_id)

                if backup_ping_settings.is_active is False:
                    continue

                now = int(time.time())
                delta_seconds = now - backup_ping_settings.last_updated_timestamp
                settings_delta_seconds = backup_ping_settings.update_timedelta * 60

                if delta_seconds < settings_delta_seconds:
                    continue

                db.update_backup_ping(chat_id)

                all_birthdays = get_all_birthdays_formatted(chat_id)
                bot.send_message(
                    chat_id,
                    f"{i18n.get_message('latest_backup', chat_id)}\n{all_birthdays}",
                    parse_mode="Markdown",
                )

        except Exception as e:
            logging.error(f"Error during backup ping processing: {e}")


def register_backup(message):
    chat_id = message.chat.id

    msg = bot.send_message(
        chat_id,
        i18n.get_message("enter_backup_interval", chat_id),
        parse_mode="Markdown",
    )

    register_backup_messages[chat_id] = [msg.message_id]

    user_states[chat_id] = TUserState.AwaitingInterval


def unregister_backup(message):
    chat_id = message.chat.id
    db.unregister_backup_ping(chat_id)
    bot.send_message(
        chat_id,
        i18n.get_message("backup_unregistered", chat_id),
        parse_mode="Markdown",
    )

    user_states[chat_id] = TUserState.Default


def handle_deletion(message):
    chat_id = message.chat.id
    all_birthdays = get_all_birthdays_formatted(chat_id, need_id=True)
    birthdays_messages = utils.split_message(all_birthdays)

    instruct_msg = bot.send_message(
        chat_id,
        i18n.get_message("enter_delete_ids", chat_id),
        parse_mode="Markdown",
    )

    birthday_deletion_messages[chat_id] = [instruct_msg.message_id]

    for birthday_message in birthdays_messages:
        msg = bot.send_message(chat_id, birthday_message, parse_mode="Markdown")
        birthday_deletion_messages[chat_id].append(msg.message_id)

    user_states[chat_id] = TUserState.AwaitingDeletion


@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    # Skip if already handled by specific handlers
    if call.data.startswith("reminder_") or call.data.startswith("lang_"):
        return

    message = call.message
    chat_id = message.chat.id

    # Map callback data to commands
    command_mapping = {
        "start": TCommand.Start,
        "backup": TCommand.Backup,
        "register_birthday": TCommand.RegisterBirthday,
        "register_backup": TCommand.RegisterBackup,
        "unregister_backup": TCommand.UnregisterBackup,
        "delete_birthday": TCommand.DeleteBirthday,
        "stats": TCommand.Stats,
        "share": TCommand.Share,
        "language": TCommand.Language,
    }

    if call.data in command_mapping:
        command = command_mapping[call.data]

        if command == TCommand.Start:
            handle_start(message)
        elif command == TCommand.Backup:
            send_backup(message)
        elif command == TCommand.RegisterBirthday:
            register_birthday(message)
        elif command == TCommand.RegisterBackup:
            register_backup(message)
        elif command == TCommand.UnregisterBackup:
            unregister_backup(message)
        elif command == TCommand.DeleteBirthday:
            handle_deletion(message)
        elif command == TCommand.Stats:
            handle_stats(message)
        elif command == TCommand.Share:
            send_share_message(message)
        elif command == TCommand.Language:
            bot.send_message(
                chat_id,
                i18n.get_button_text("language", chat_id),
                reply_markup=get_language_keyboard(),
                parse_mode="Markdown",
            )
        else:
            bot.answer_callback_query(
                call.id, i18n.get_message("unknown_command", chat_id)
            )
    else:
        bot.answer_callback_query(call.id, i18n.get_message("invalid_action", chat_id))


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    user_message = message.text.strip()

    if user_message == "/clear":
        # Secret command to clear keyboard
        bot.delete_message(chat_id, message.message_id)
        # Remove keyboard and clean up that message
        remove_keyboard(message)
        return

    # Handle text commands (like /start)
    if user_message in COMMAND_MAPPINGS:
        command = COMMAND_MAPPINGS[user_message]
        if command == TCommand.Start:
            handle_start(message)
            return
        elif command == TCommand.Backup:
            send_backup(message)
            return
        elif command == TCommand.RegisterBirthday:
            register_birthday(message)
            return
        elif command == TCommand.RegisterBackup:
            register_backup(message)
            return
        elif command == TCommand.UnregisterBackup:
            unregister_backup(message)
            return
        elif command == TCommand.DeleteBirthday:
            handle_deletion(message)
            return
        elif command == TCommand.Stats:
            handle_stats(message)
            return
        elif command == TCommand.Share:
            send_share_message(message)
            return

    # Handle button texts in user's language
    button_mapping = get_button_to_command_mapping(chat_id)
    if user_message in button_mapping:
        command = button_mapping[user_message]
        if command == TCommand.Start:
            handle_start(message)
            return
        elif command == TCommand.Backup:
            send_backup(message)
            return
        elif command == TCommand.RegisterBirthday:
            register_birthday(message)
            return
        elif command == TCommand.RegisterBackup:
            register_backup(message)
            return
        elif command == TCommand.UnregisterBackup:
            unregister_backup(message)
            return
        elif command == TCommand.DeleteBirthday:
            handle_deletion(message)
            return
        elif command == TCommand.Stats:
            handle_stats(message)
            return
        elif command == TCommand.Share:
            send_share_message(message)
            return

    match user_states.get(chat_id):
        case TUserState.AwaitingInterval:
            try:
                if not utils.is_timestamp_valid(user_message):
                    raise ValueError(f"Invalid format, user_message: {user_message}")

                interval_in_minutes = utils.get_time(user_message)

                db.register_backup_ping(chat_id, interval_in_minutes)

                bot.send_message(
                    chat_id,
                    i18n.get_message(
                        "backup_registered", chat_id, interval=interval_in_minutes
                    ),
                    parse_mode="Markdown",
                )

                user_states[chat_id] = TUserState.Default

                bot.delete_message(chat_id, message.message_id)

                for old_message_id in register_backup_messages[chat_id]:
                    bot.delete_message(chat_id, old_message_id)

                if chat_id in register_backup_messages.keys():
                    del register_backup_messages[chat_id]

            except Exception:
                error_msg = bot.send_message(
                    chat_id,
                    i18n.get_message("invalid_interval_format", chat_id),
                    parse_mode="Markdown",
                )

                register_backup_messages[chat_id].append(error_msg.message_id)

        case TUserState.AwaitingDeletion:
            try:
                birthday_ids = [
                    int(id_str.strip()) for id_str in user_message.split(",")
                ]
                deleted_ids = []
                not_found_ids = []

                for birthday_id in birthday_ids:
                    deleted_rows = db.delete_birthday(chat_id, birthday_id)
                    if deleted_rows > 0:
                        deleted_ids.append(birthday_id)
                    else:
                        not_found_ids.append(birthday_id)

                if deleted_ids:
                    bot.send_message(
                        chat_id,
                        i18n.get_message(
                            "birthdays_deleted",
                            chat_id,
                            ids=", ".join(map(str, deleted_ids)),
                        ),
                        parse_mode="Markdown",
                    )

                if not_found_ids:
                    bot.send_message(
                        chat_id,
                        i18n.get_message(
                            "birthdays_not_found",
                            chat_id,
                            ids=", ".join(map(str, not_found_ids)),
                        ),
                        parse_mode="Markdown",
                    )
                    logging.warning(
                        f"Could not find birthdays for Chat ID {chat_id}: {not_found_ids}"
                    )

                user_states[chat_id] = TUserState.Default

                birthday_deletion_messages[chat_id].append(message.message_id)

                for old_message_id in birthday_deletion_messages[chat_id]:
                    bot.delete_message(chat_id, old_message_id)

                if chat_id in birthday_deletion_messages.keys():
                    del birthday_deletion_messages[chat_id]

            except ValueError:
                error_msg = bot.send_message(
                    chat_id,
                    i18n.get_message("invalid_ids_format", chat_id),
                    parse_mode="Markdown",
                )
                birthday_deletion_messages[chat_id].append(error_msg.message_id)
            except Exception as e:
                logging.error(f"Error deleting birthdays for Chat ID {chat_id}: {e}")

        case TUserState.AwaitingBirthday:
            try:
                success, error_message = utils.validate_birthday_input(
                    user_message, chat_id
                )
                if not success:
                    err_msg = bot.send_message(
                        chat_id,
                        error_message,
                        parse_mode="Markdown",
                    )
                    birthday_registration_messages[chat_id].add(err_msg.message_id)
                    return

                success, parsed_birthdays = utils.parse_dates(user_message)
                for name, parsed_date, has_year in parsed_birthdays:
                    db.register_birthday(chat_id, name, parsed_date, has_year)

                birthday_msg = ""
                for name, parsed_date, has_year in parsed_birthdays:
                    if has_year:
                        birthday_msg += (
                            f"- {name}: {parsed_date.strftime('%d %B %Y')}\n"
                        )
                    else:
                        birthday_msg += f"- {name}: {parsed_date.strftime('%d %B')}\n"

                bot.send_message(
                    chat_id,
                    f"{i18n.get_message('birthdays_registered', chat_id)}\n{birthday_msg}",
                    parse_mode="Markdown",
                )

                user_states[chat_id] = TUserState.Default

                bot.delete_message(chat_id, message.message_id)

                for old_message_id in birthday_registration_messages[chat_id]:
                    bot.delete_message(chat_id, old_message_id)

                if chat_id in birthday_registration_messages.keys():
                    del birthday_registration_messages[chat_id]

            except Exception:
                bot.send_message(
                    chat_id,
                    i18n.get_message("invalid_name_format", chat_id),
                    parse_mode="Markdown",
                )
        case _:
            pass


def log_cleaner():
    """Thread function to periodically clean up old log files."""
    while True:
        try:
            utils.cleanup_old_logs()
            time.sleep(24 * 60 * 60)
        except Exception as e:
            logging.error(f"Error in log cleaner thread: {e}")
            utils.log_exception(e)
            time.sleep(60 * 60)


if __name__ == "__main__":
    db.init_db()

    logging.info("Bot is running...")
    try:
        logging.info("Starting backup ping thread...")
        backup_thread = threading.Thread(target=process_backup_pings, daemon=True)
        backup_thread.start()

        logging.info("Starting birthday ping thread...")
        birthday_thread = threading.Thread(target=process_birthday_pings, daemon=True)
        birthday_thread.start()

        logging.info("Starting log cleaner thread...")
        log_cleaner_thread = threading.Thread(target=log_cleaner, daemon=True)
        log_cleaner_thread.start()

        bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)

    except KeyboardInterrupt:
        logging.info("Shutting down bot gracefully...")

        backup_thread.join(timeout=2)
        birthday_thread.join(timeout=2)
        log_cleaner_thread.join(timeout=2)

    except Exception as e:
        logging.critical(f"Bot polling encountered an error: {e}")
        utils.log_exception(e)
