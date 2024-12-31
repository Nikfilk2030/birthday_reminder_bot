import asyncio
import logging
import os
import mysql.connector
import time

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

DB_HOST = "mysql"
DB_USER = "root"
DB_PASSWORD = "rootpassword"
DB_DATABASE = "telegram_bot"


def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_DATABASE
    )


# Command: '/start' - Register the user
async def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    # Save user to DB if not already
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT IGNORE INTO users (telegram_id) VALUES (%s)", (user_id,)
    )
    conn.commit()
    conn.close()
    await update.message.reply_text("You are now registered! Use /configure to set up your messages.")


# Command: '/configure' - Configure messages
async def configure(update: Update, context: CallbackContext):
    try:
        # User must send: <Interval (mins)> <Message> <Count>
        user_id = update.effective_user.id
        args = context.args
        if len(args) < 3:
            await update.message.reply_text(
                "Usage: /configure <Interval (mins)> <Message> <Count>"
            )
            return

        interval = int(args[0])
        message = " ".join(args[1:-1])  # Everything except last argument is the message
        count = int(args[-1])

        # Save configuration to the DB
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO user_configuration (telegram_id, message, interval_minutes, remaining_count)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            message = VALUES(message), interval_minutes = VALUES(interval_minutes), remaining_count = VALUES(remaining_count)
            """,
            (user_id, message, interval, count),
        )
        conn.commit()
        conn.close()
        await update.message.reply_text("Configuration saved successfully!")
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("An error occurred. Please try again!")


# Function to send pings
async def send_pings(context: CallbackContext):
    job = context.job
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch message configurations for the user
    cursor.execute("SELECT * FROM user_configuration WHERE remaining_count > 0")
    rows = cursor.fetchall()

    if not rows:
        return

    for row in rows:
        telegram_id = row["telegram_id"]
        message = row["message"]
        remaining_count = row["remaining_count"]

        # Send message
        try:
            await context.bot.send_message(chat_id=telegram_id, text=message)
            remaining_count -= 1  # Decrease count
            cursor.execute(
                "UPDATE user_configuration SET remaining_count = %s WHERE id = %s",
                (remaining_count, row["id"]),
            )
            conn.commit()
        except Exception as e:
            logger.error(f"Could not send message to {telegram_id}: {e}")

    conn.close()


# Function to handle missed pings
def handle_missed_pings():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    one_hour_ago = datetime.now() - timedelta(hours=1)
    cursor.execute("SELECT * FROM user_configuration WHERE last_sent < %s", (one_hour_ago,))
    rows = cursor.fetchall()

    for row in rows:
        # Calculate the number of missed pings and send them
        raise Exception('bebra')


def main():
    logger.info("bebra1")

    # Set up scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=handle_missed_pings, trigger="interval", hours=1, id="missed_pings_job")
    scheduler.start()

    logger.info("bebra2")

    # Telegram bot setup
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("configure", configure))

    job_queue = application.job_queue
    job_queue.run_repeating(send_pings, interval=60, first=10)  # Run every minute

    application.run_polling()


if __name__ == "__main__":
    logger.info("bebra3")
    asyncio.get_event_loop().run_until_complete(main())
