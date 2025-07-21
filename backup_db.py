#!/usr/bin/env python3
"""
Database backup utility for Birthday Reminder Bot
Creates multiple types of backups for maximum safety
"""

import os
import sqlite3
import subprocess
from datetime import datetime

def create_backup():
    """Creates backup of the main database"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Ensure backup directory exists
    os.makedirs("backups", exist_ok=True)

    # Only backup if main database exists
    if not os.path.exists("data.db"):
        print("❌ Main database data.db not found!")
        return False

    try:
        # 1. Simple file copy
        subprocess.run([
            "cp", "data.db", f"backups/data_backup_{timestamp}.db"
        ], check=True)

        # 2. SQLite .backup command
        subprocess.run([
            "sqlite3", "data.db", f".backup backups/data_sqlite_backup_{timestamp}.db"
        ], check=True)

        # 3. SQL dump
        with open(f"backups/data_dump_{timestamp}.sql", "w") as f:
            subprocess.run([
                "sqlite3", "data.db", ".dump"
            ], stdout=f, check=True)

        print(f"✅ Backup created successfully: {timestamp}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Backup failed: {e}")
        return False

def restore_from_backup(backup_file):
    """Restore database from backup file"""
    if not os.path.exists(backup_file):
        print(f"❌ Backup file {backup_file} not found!")
        return False

    try:
        # Create restore point first
        if os.path.exists("data.db"):
            create_backup()

        # Restore from backup
        subprocess.run(["cp", backup_file, "data.db"], check=True)
        print(f"✅ Database restored from {backup_file}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Restore failed: {e}")
        return False

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "restore":
        if len(sys.argv) < 3:
            print("Usage: python backup_db.py restore <backup_file>")
            sys.exit(1)
        restore_from_backup(sys.argv[2])
    else:
        create_backup()
