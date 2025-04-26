# Internationalization (i18n) Improvements for Dmarket Telegram Bot

This document outlines the implementation of a comprehensive internationalization (i18n) system for the Dmarket Telegram Bot project, addressing one of the key improvement areas identified in the repository analysis.

## Overview

The internationalization system will enable:
- Multi-language support for user-facing messages
- Consistent language usage throughout the codebase
- Automatic language detection for users
- Easy addition of new languages

## Implementation Details

### 1. Standardization of Codebase Language

#### Current Issues:
- Mixed usage of Russian and English in comments and documentation
- Inconsistent error messages in different languages
- Lack of language standards across modules

#### Solution:
- Standardize all code comments, variable names, and documentation to English
- Create a translation system for user-facing messages
- Establish coding standards for language usage

### 2. Translation System

We'll implement a translation system using the `gettext` library, which is the standard for internationalization in Python applications.

#### Directory Structure:
```
Dmarket_Telegram_bot/
├── locale/
│   ├── en/
│   │   └── LC_MESSAGES/
│   │       └── messages.po
│   ├── ru/
│   │   └── LC_MESSAGES/
│   │       └── messages.po
│   └── uk/
│       └── LC_MESSAGES/
│           └── messages.po
├── i18n/
│   ├── __init__.py
│   ├── translator.py
│   └── language_detector.py
```

#### Core Components:

1. **Translator Class**:
```python
import gettext
import os
from typing import Dict, Optional

class Translator:
    """
    Handles translation of messages to different languages.
    
    This class provides a simple interface for translating messages
    using the gettext library. It supports multiple languages and
    fallback to a default language if a translation is not available.
    """
    
    def __init__(self, domain: str = "messages", locale_dir: str = "locale", default_language: str = "en"):
        """
        Initialize the translator.
        
        Args:
            domain: The gettext domain (usually the name of the .po file without extension)
            locale_dir: Directory containing the locale files
            default_language: Fallback language if requested language is not available
        """
        self.domain = domain
        self.locale_dir = os.path.abspath(locale_dir)
        self.default_language = default_language
        self.translations: Dict[str, gettext.GNUTranslations] = {}
        
        # Load available translations
        self._load_translations()
    
    def _load_translations(self) -> None:
        """Load all available translations from the locale directory."""
        if not os.path.exists(self.locale_dir):
            os.makedirs(self.locale_dir)
            
        # Load default language first
        self.translations[self.default_language] = gettext.translation(
            self.domain,
            self.locale_dir,
            languages=[self.default_language],
            fallback=True
        )
        
        # Load other available languages
        for lang_dir in os.listdir(self.locale_dir):
            lang_path = os.path.join(self.locale_dir, lang_dir)
            if os.path.isdir(lang_path) and lang_dir != self.default_language:
                try:
                    self.translations[lang_dir] = gettext.translation(
                        self.domain,
                        self.locale_dir,
                        languages=[lang_dir]
                    )
                except FileNotFoundError:
                    # Skip languages without translation files
                    continue
    
    def translate(self, message: str, language: str = None) -> str:
        """
        Translate a message to the specified language.
        
        Args:
            message: The message to translate
            language: The target language code (e.g., 'en', 'ru')
            
        Returns:
            The translated message, or the original message if translation is not available
        """
        if not language:
            language = self.default_language
            
        if language in self.translations:
            return self.translations[language].gettext(message)
        
        # Fallback to default language
        return self.translations[self.default_language].gettext(message)
    
    def get_available_languages(self) -> list:
        """Return a list of available language codes."""
        return list(self.translations.keys())
```

2. **Language Detector**:
```python
from typing import Optional
import re

class LanguageDetector:
    """
    Detects user's preferred language based on various signals.
    
    This class provides methods to detect a user's preferred language
    based on Telegram user settings, message content, or explicit selection.
    """
    
    def __init__(self, default_language: str = "en", available_languages: list = None):
        """
        Initialize the language detector.
        
        Args:
            default_language: Fallback language if detection fails
            available_languages: List of supported language codes
        """
        self.default_language = default_language
        self.available_languages = available_languages or ["en", "ru"]
        
        # User language preferences cache
        self.user_languages = {}
    
    def detect_from_telegram(self, user_data: dict) -> str:
        """
        Detect language from Telegram user data.
        
        Args:
            user_data: Telegram user data containing language_code
            
        Returns:
            Detected language code or default language
        """
        if not user_data or "language_code" not in user_data:
            return self.default_language
            
        lang_code = user_data["language_code"]
        
        # Map Telegram language codes to our supported languages
        if lang_code.startswith("ru"):
            return "ru"
        elif lang_code.startswith("uk"):
            return "uk"
        elif lang_code in self.available_languages:
            return lang_code
            
        return self.default_language
    
    def set_user_language(self, user_id: int, language: str) -> None:
        """
        Set a user's preferred language.
        
        Args:
            user_id: Telegram user ID
            language: Language code
        """
        if language in self.available_languages:
            self.user_languages[user_id] = language
    
    def get_user_language(self, user_id: int, user_data: dict = None) -> str:
        """
        Get a user's preferred language.
        
        Args:
            user_id: Telegram user ID
            user_data: Optional Telegram user data for first-time detection
            
        Returns:
            User's preferred language code
        """
        # Check if we have a stored preference
        if user_id in self.user_languages:
            return self.user_languages[user_id]
            
        # Try to detect from Telegram data
        if user_data:
            detected = self.detect_from_telegram(user_data)
            self.user_languages[user_id] = detected
            return detected
            
        return self.default_language
```

3. **Integration with Telegram Bot**:

```python
from i18n.translator import Translator
from i18n.language_detector import LanguageDetector

# Initialize the translator and language detector
translator = Translator(domain="messages", locale_dir="../locale", default_language="en")
language_detector = LanguageDetector(
   default_language="en",
   available_languages=translator.get_available_languages()
)


# Create a shorthand function for translation
def _(message: str, user_id: int = None, user_data: dict = None) -> str:
   """
   Translate a message for a specific user.
   
   Args:
       message: Message to translate
       user_id: Telegram user ID
       user_data: Telegram user data
       
   Returns:
       Translated message
   """
   if user_id is not None:
      language = language_detector.get_user_language(user_id, user_data)
   else:
      language = "en"

   return translator.translate(message, language)


# Example usage in a Telegram handler
async def start_command(update, context):
   user = update.effective_user
   user_id = user.id

   # Get user's language
   language = language_detector.get_user_language(user_id, user.to_dict())

   # Translate welcome message
   welcome_message = _("Welcome to DMarket Telegram Bot!", user_id)

   # Send translated message
   await update.message.reply_text(welcome_message)

   # Add language selection buttons
   keyboard = [
      [InlineKeyboardButton("English 🇬🇧", callback_data="lang_en")],
      [InlineKeyboardButton("Pycckuй 🇷🇺", callback_data="lang_ru")],
      [InlineKeyboardButton("Ykpaїhc'ka 🇺🇦", callback_data="lang_uk")]
   ]
   reply_markup = InlineKeyboardMarkup(keyboard)

   await update.message.reply_text(
      _("Please select your preferred language:", user_id),
      reply_markup=reply_markup
   )


# Language selection callback
async def language_callback(update, context):
   query = update.callback_query
   user_id = query.from_user.id

   # Extract language code from callback data
   lang_code = query.data.split("_")[1]

   # Set user's language preference
   language_detector.set_user_language(user_id, lang_code)

   # Confirm language selection
   await query.answer()
   await query.edit_message_text(
      _("Language set to {}", user_id).format(
         {"en": "English", "ru": "Pycckuй", "uk": "Ykpaїhc'ka"}[lang_code]
      )
   )
```

### 3. Message Extraction and Translation Workflow

1. **Extract Messages**:
   - Use the `pygettext` tool to extract translatable strings from Python code
   - Command: `pygettext -d messages -o locale/messages.pot path/to/your/code`

2. **Create Language Files**:
   - For each supported language, create a .po file from the template
   - Command: `msginit -i locale/messages.pot -o locale/ru/LC_MESSAGES/messages.po -l ru`

3. **Translate Messages**:
   - Edit .po files with translations for each language
   - Use tools like Poedit for easier translation management

4. **Compile Message Files**:
   - Compile .po files to binary .mo files for faster loading
   - Command: `msgfmt -o locale/ru/LC_MESSAGES/messages.mo locale/ru/LC_MESSAGES/messages.po`

### 4. Code Refactoring Guidelines

To standardize the codebase language:

1. **Comments and Documentation**:
   - Translate all Russian comments to English
   - Use clear and concise English for all new comments
   - Update docstrings to follow English conventions

2. **Variable and Function Names**:
   - Use English names for all variables, functions, and classes
   - Follow PEP 8 naming conventions

3. **User-Facing Messages**:
   - Wrap all user-facing strings with the translation function
   - Example: `_("Your message here")`
   - Use string formatting with named parameters for better translation support
   - Example: `_("Hello, {name}!").format(name=user_name)`

## Usage Examples

### Basic Translation

```python
from i18n import _

# Simple translation
message = _("Item price has changed")

# Translation with formatting
message = _("Item {item_name} price changed to ${price}").format(
    item_name="AWP | Dragon Lore",
    price=1299.99
)
```

### User Language Management

```python
from i18n import language_detector

# Set user language preference
language_detector.set_user_language(user_id=123456789, language="ru")

# Get user language
user_lang = language_detector.get_user_language(user_id=123456789)

# Translate message for specific user
from i18n import _
message = _("Welcome back!", user_id=123456789)
```

### Adding a New Language

1. Extract messages:
```bash
pygettext -d messages -o locale/messages.pot .
```

2. Create language file:
```bash
msginit -i locale/messages.pot -o locale/de/LC_MESSAGES/messages.po -l de
```

3. Translate messages in the .po file

4. Compile the .mo file:
```bash
msgfmt -o locale/de/LC_MESSAGES/messages.mo locale/de/LC_MESSAGES/messages.po
```

5. Add the language to the available languages list:
```python
language_detector = LanguageDetector(
    default_language="en",
    available_languages=["en", "ru", "uk", "de"]
)
```

## Implementation Plan

1. **Phase 1: Setup Translation Infrastructure**
   - Create the i18n module with Translator and LanguageDetector classes
   - Set up the locale directory structure
   - Create initial message template

2. **Phase 2: Refactor User-Facing Components**
   - Update Telegram bot handlers to use the translation system
   - Add language selection command and callback
   - Implement user language preference storage

3. **Phase 3: Standardize Codebase**
   - Translate Russian comments and documentation to English
   - Update variable and function names to follow English conventions
   - Wrap all user-facing strings with translation function

4. **Phase 4: Add Initial Languages**
   - Create translation files for English (default)
   - Add Russian translation
   - Add Ukrainian translation

5. **Phase 5: Testing and Documentation**
   - Test the translation system with different languages
   - Document the translation workflow for contributors
   - Create guidelines for adding new languages

## Benefits

Implementing this internationalization system will:

1. Improve user experience for non-English speakers
2. Standardize the codebase for better maintainability
3. Make the project more accessible to international contributors
4. Provide a foundation for supporting additional languages in the future
5. Address one of the lowest-rated aspects of the project (6/10)

## Conclusion

The proposed internationalization system provides a comprehensive solution for adding multi-language support to the Dmarket Telegram Bot. By implementing this system, we can significantly improve the user experience for international users and address one of the key improvement areas identified in the repository analysis.