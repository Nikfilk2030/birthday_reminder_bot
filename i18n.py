"""
Internationalization (i18n) module for Birthday Reminder Bot
Handles translations and language switching
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

import db


class I18n:
    """Internationalization class for managing translations"""

    def __init__(self, translations_file: str = "translations.json"):
        self.translations_file = translations_file
        self.translations: Dict[str, Any] = {}
        self.default_language = "en"
        self.supported_languages = ["en", "ru"]
        self.load_translations()

    def load_translations(self) -> None:
        """Load translations from JSON file"""
        try:
            translations_path = Path(self.translations_file)
            if translations_path.exists():
                with open(translations_path, "r", encoding="utf-8") as f:
                    self.translations = json.load(f)
                logging.info(f"Loaded translations from {self.translations_file}")
            else:
                logging.error(f"Translations file {self.translations_file} not found!")
                self.translations = {}
        except Exception as e:
            logging.error(f"Error loading translations: {e}")
            self.translations = {}

    def get_user_language(self, chat_id: int) -> str:
        """Get user's language preference"""
        lang = db.get_user_language(chat_id)
        return lang if lang in self.supported_languages else self.default_language

    def set_user_language(self, chat_id: int, language_code: str) -> bool:
        """Set user's language preference"""
        if language_code not in self.supported_languages:
            return False

        db.set_user_language(chat_id, language_code)
        return True

    def get_text(self, key: str, chat_id: int, **kwargs) -> str:
        """
        Get translated text by key for specific user

        Args:
            key: Translation key in format "category.key" (e.g., "buttons.start")
            chat_id: User's chat ID
            **kwargs: Variables for string formatting

        Returns:
            Translated text with variables substituted
        """
        language = self.get_user_language(chat_id)
        return self._get_text_by_lang(key, language, **kwargs)

    def get_text_by_lang(self, key: str, language: str, **kwargs) -> str:
        """
        Get translated text by key for specific language

        Args:
            key: Translation key in format "category.key"
            language: Language code ("en", "ru")
            **kwargs: Variables for string formatting
        """
        return self._get_text_by_lang(key, language, **kwargs)

    def _get_text_by_lang(self, key: str, language: str, **kwargs) -> str:
        """Internal method to get text by language"""
        try:
            # Navigate through nested dictionary using dot notation
            parts = key.split(".")
            current = self.translations

            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    # Key not found, return key itself as fallback
                    logging.warning(f"Translation key '{key}' not found")
                    return key

            # Get translation for specific language
            if isinstance(current, dict) and language in current:
                text = current[language]
            elif isinstance(current, dict) and self.default_language in current:
                # Fallback to default language
                text = current[self.default_language]
                logging.warning(
                    f"Translation for '{key}' not found in '{language}', using '{self.default_language}'"
                )
            else:
                # No translation found
                logging.warning(f"No translation found for '{key}' in any language")
                return key

            # Format the text with provided variables
            if kwargs:
                try:
                    text = text.format(**kwargs)
                except KeyError as e:
                    logging.warning(f"Missing variable {e} for translation '{key}'")
                    # Return text without formatting
                    pass
                except Exception as e:
                    logging.error(f"Error formatting translation '{key}': {e}")

            return text

        except Exception as e:
            logging.error(f"Error getting translation for '{key}': {e}")
            return key

    def get_month_name(self, month_name: str, chat_id: int) -> str:
        """Get translated month name"""
        return self.get_text(f"month_names.{month_name}", chat_id)

    def get_button_text(self, button_key: str, chat_id: int) -> str:
        """Get translated button text"""
        return self.get_text(f"buttons.{button_key}", chat_id)

    def get_button_description(self, button_key: str, chat_id: int) -> str:
        """Get translated button description"""
        return self.get_text(f"button_descriptions.{button_key}", chat_id)

    def get_message(self, message_key: str, chat_id: int, **kwargs) -> str:
        """Get translated message"""
        return self.get_text(f"messages.{message_key}", chat_id, **kwargs)


# Global instance
i18n = I18n()


# Convenience functions
def get_text(key: str, chat_id: int, **kwargs) -> str:
    """Convenience function to get translated text"""
    return i18n.get_text(key, chat_id, **kwargs)


def get_user_language(chat_id: int) -> str:
    """Convenience function to get user language"""
    return i18n.get_user_language(chat_id)


def set_user_language(chat_id: int, language_code: str) -> bool:
    """Convenience function to set user language"""
    return i18n.set_user_language(chat_id, language_code)


def get_message(message_key: str, chat_id: int, **kwargs) -> str:
    """Convenience function to get translated message"""
    return i18n.get_message(message_key, chat_id, **kwargs)


def get_button_text(button_key: str, chat_id: int) -> str:
    """Convenience function to get translated button text"""
    return i18n.get_button_text(button_key, chat_id)


def get_button_description(button_key: str, chat_id: int) -> str:
    """Convenience function to get translated button description"""
    return i18n.get_button_description(button_key, chat_id)


def get_month_name(month_name: str, chat_id: int) -> str:
    """Convenience function to get translated month name"""
    return i18n.get_month_name(month_name, chat_id)
