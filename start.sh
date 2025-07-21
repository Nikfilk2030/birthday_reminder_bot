#!/bin/bash

# Help function
show_help() {
    echo "Birthday Reminder Bot Launcher"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --prestable    Run in prestable mode (uses PRESTABLE_TELEGRAM_BOT_TOKEN)"
    echo "  --production   Run in production mode (default, uses TELEGRAM_BOT_TOKEN)"
    echo "  --no-docker    Run without Docker (direct Python execution)"
    echo "  --help, -h     Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                # Run in production mode with Docker"
    echo "  $0 --prestable   # Run in prestable mode with Docker"
    echo "  $0 --no-docker   # Run in production mode without Docker"
    echo "  $0 --prestable --no-docker  # Run in prestable mode without Docker"
}

# Parse command line arguments
PRESTABLE_MODE=false
USE_DOCKER=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --prestable)
            PRESTABLE_MODE=true
            shift
            ;;
        --production)
            PRESTABLE_MODE=false
            shift
            ;;
        --no-docker)
            USE_DOCKER=false
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Create backup before running
echo "🔒 Creating backup before startup..."
python3 backup_db.py

# Set environment variables
if [ "$PRESTABLE_MODE" = true ]; then
    export PRESTABLE_MODE=true
    echo "🧪 Starting in PRESTABLE mode..."
else
    export PRESTABLE_MODE=false
    echo "🚀 Starting in PRODUCTION mode..."
fi

# Code formatting (only if not in prestable mode to avoid disrupting production)
if [ "$PRESTABLE_MODE" = false ]; then
    echo "🔧 Formatting code..."
    black .
    isort .
    flake8 .
fi

if [ "$USE_DOCKER" = true ]; then
    # Docker running
    echo "🐳 Starting with Docker..."
    sudo docker compose down
    sudo docker compose up --build
else
    # Direct Python execution
    echo "🐍 Starting with Python directly..."
    python3 bot.py
fi
