# 🎂 Birthday Reminder Telegram Bot

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10-blue.svg">
  <img src="https://img.shields.io/badge/License-MIT-green.svg">
  <img src="https://img.shields.io/badge/Platform-Telegram-blue.svg">
  <img src="https://img.shields.io/badge/Docker-Ready-blue.svg">
</p>

Never miss a birthday again! Birthday Reminder Bot is a Telegram bot that helps you keep track of birthdays and sends timely reminders. Born out of a personal need after missing a best friend's birthday, this bot ensures you'll always remember important dates.

## 🌟 Features

- 📝 Store birthdays with or without birth years
- ⏰ Customizable reminder settings (0, 1, 3, or 7 days before)
- 💾 Automatic backup system
- 🌍 Supports multiple date formats
- 🔒 Private data storage for each user
- 🌙 Smart notification system (only sends during daytime)
- 🐳 Docker support for easy deployment

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- Docker (optional)
- Telegram Bot Token (get it from [@BotFather](https://t.me/botfather))

### Installation

1. Clone the repository:

```bash
git clone https://github.com/Nikfilk2030/birthday_reminder_bot.git
cd birthday_reminder_bot
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create and configure your `.env` file:

```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

4. Choose your preferred deployment method:

#### Using Docker (Recommended)

```bash
docker compose up --build
```

#### Manual Installation

```bash
./start.sh
```

## 💡 Usage

### Basic Commands

- `/start` - Initialize the bot and see available commands
- `/register_birthday` - Add a new birthday
- `/delete_birthday` - Remove a birthday
- `/backup` - Get a list of all saved birthdays
- `/register_backup` - Set up automatic backups
- `/unregister_backup` - Disable automatic backups

### Date Input Formats

The bot accepts various date formats:
- `DD.MM.YYYY` (e.g., 15.06.1990)
- `DD.MM` (e.g., 15.06)
- `DD.MM AGE` (e.g., 15.06 25)

Example:

```
John Doe
15.06.1990
```

### Reminder Settings

Choose when to receive reminders:
- On the birthday (0 days)
- 1 day before
- 3 days before
- 7 days before

## 🛠 Technical Details

### Project Structure

```
birthday_reminder_bot/
├── bot.py # Main bot logic
├── db.py # Database operations
├── utils.py # Utility functions
├── tests.py # Unit tests
├── docker-compose.yml # Docker configuration
├── Dockerfile # Docker build instructions
└── requirements.txt # Python dependencies
```

### Database Schema

The bot uses SQLite with the following main tables:
- `birthdays` - Stores birthday information
- `user_reminder_settings` - User notification preferences
- `backup_ping_settings` - Automatic backup configurations

### Testing

Run the test suite:

```bash
python tests.py
```

## 🔐 Privacy & Security

- All data is stored locally in SQLite databases
- Each user's data is isolated by their chat ID
- No personal information is shared between users
- Automatic log rotation (30 days retention)

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Setup

1. Install development dependencies:

```bash
pip install black isort flake8
```

2. Use the provided `start.sh` script for development:

```bash
./start.sh
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI) for the excellent Telegram bot framework
- The open-source community for inspiration and tools

## 📧 Contact

Telegram: [@pchelka_zh](https://t.me/pchelka_zh)

## 🚀 Future Plans

- [ ] Multi-language support
- [ ] Birthday statistics and analytics
- [ ] Export/Import functionality
- [ ] Web interface for management
- [ ] Group birthday notifications
