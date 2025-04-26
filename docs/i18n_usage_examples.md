# Internationalization (i18n) Usage Examples

This document provides practical examples of how to use the internationalization (i18n) system in the Dmarket Telegram Bot project.

## Basic Usage

### Importing the Translation Function

```python
from i18n import _

# Simple translation
message = _("Welcome to DMarket Telegram Bot!")
```

### Translation with User Context

```python
from i18n import _

# Get user ID from Telegram message
user_id = message.from_user.id

# Translate with user context
welcome_message = _("Welcome to DMarket Telegram Bot!", user_id=user_id)
```

### Translation with Formatting

```python
from i18n import _

# Translation with string formatting
message = _("Item {item_name} price changed to ${price}").format(
    item_name="AWP | Dragon Lore",
    price=1299.99
)
```

## Integration with Telegram Bot

### Message Handlers

```python
from aiogram import types
from i18n import _

async def start_command(message: types.Message):
    user = message.from_user
    user_id = user.id
    
    # Translate welcome message based on user's language preference
    welcome_message = _("Welcome to DMarket Telegram Bot!", user_id=user_id)
    
    # Send translated message
    await message.reply(welcome_message)
```

### Callback Handlers

```python
from aiogram import types
from i18n import _

async def process_callback(query: types.CallbackQuery):
    user_id = query.from_user.id
    
    # Answer callback query with translated message
    await query.answer(_("Processing your request...", user_id=user_id))
    
    # Edit message with translated text
    await query.message.edit_text(
        _("Your request has been processed.", user_id=user_id)
    )
```

### Error Messages

```python
from aiogram import types
from i18n import _

async def handle_error(message: types.Message, error_code: str):
    user_id = message.from_user.id
    
    error_messages = {
        "not_found": _("Item not found.", user_id=user_id),
        "permission_denied": _("You don't have permission to perform this action.", user_id=user_id),
        "invalid_input": _("Invalid input. Please try again.", user_id=user_id)
    }
    
    error_message = error_messages.get(
        error_code, 
        _("An unknown error occurred.", user_id=user_id)
    )
    
    await message.reply(error_message)
```

## Language Management

### Setting User Language

```python
from i18n import language_detector

# Set user language preference
user_id = 123456789
language_detector.set_user_language(user_id, "ru")
```

### Getting User Language

```python
from i18n import language_detector

# Get user language preference
user_id = 123456789
user_language = language_detector.get_user_language(user_id)

print(f"User {user_id} language: {user_language}")
```

### Language Selection Interface

See the complete implementation in `bot_handlers/language_handler.py` for a full example of a language selection interface.

## Working with Templates

### Message Templates with Multiple Translations

```python
from i18n import _

def get_price_change_message(item_name: str, old_price: float, new_price: float, user_id: int = None):
    if new_price > old_price:
        return _("Price increased: {item_name} - ${old_price} → ${new_price} (+${diff})", user_id=user_id).format(
            item_name=item_name,
            old_price=old_price,
            new_price=new_price,
            diff=round(new_price - old_price, 2)
        )
    else:
        return _("Price decreased: {item_name} - ${old_price} → ${new_price} (-${diff})", user_id=user_id).format(
            item_name=item_name,
            old_price=old_price,
            new_price=new_price,
            diff=round(old_price - new_price, 2)
        )
```

### Handling Plurals

Plurals are handled automatically by the gettext system. In your .po files, you can define different translations for singular and plural forms:

```
msgid "Found {count} item"
msgid_plural "Found {count} items"
msgstr[0] "Haйдeh {count} npeдmet"
msgstr[1] "Haйдeho {count} npeдmeta"
msgstr[2] "Haйдeho {count} npeдmetoв"
```

Then in your code:

```python
from i18n import translator

def get_items_count_message(count: int, user_id: int = None):
    # Get user language
    language = language_detector.get_user_language(user_id)
    
    # Get translation based on count
    if language == "en":
        if count == 1:
            template = translator.translate("Found {count} item", language)
        else:
            template = translator.translate("Found {count} items", language)
    else:
        # For languages with more complex plural forms, you'll need to handle them manually
        # or use a more advanced plural handling system
        if language == "ru" or language == "uk":
            if count % 10 == 1 and count % 100 != 11:
                template = translator.translate("Found {count} item", language)
            elif 2 <= count % 10 <= 4 and (count % 100 < 10 or count % 100 >= 20):
                template = translator.translate("Found {count} items", language)
            else:
                template = translator.translate("Found {count} items", language)
    
    return template.format(count=count)
```

## Adding New Translations

### Extracting Messages

To extract translatable messages from your code, use the `pygettext` tool:

```bash
pygettext -d messages -o locale/messages.pot path/to/your/code
```

### Creating Language Files

To create a new language file from the template:

```bash
msginit -i locale/messages.pot -o locale/de/LC_MESSAGES/messages.po -l de
```

### Compiling Message Files

After translating the messages in the .po file, compile it to a binary .mo file:

```bash
msgfmt -o locale/de/LC_MESSAGES/messages.mo locale/de/LC_MESSAGES/messages.po
```

### Adding the Language to the Available Languages

```python
from i18n import language_detector

# Add German to available languages
if "de" not in language_detector.available_languages:
    language_detector.available_languages.append("de")
```

## Best Practices

1. **Use Named Placeholders**: Always use named placeholders in your translations to make them more maintainable and easier to translate:
   ```python
   # Good
   _("Hello, {name}!").format(name=user_name)
   
   # Avoid
   _("Hello, {}!").format(user_name)
   ```

2. **Provide Context**: Add comments in your code to provide context for translators:
   ```python
   # Translators: This is shown when a user first starts the bot
   welcome_message = _("Welcome to DMarket Telegram Bot!")
   ```

3. **Keep Translations Simple**: Avoid complex string concatenation or formatting in your code. Instead, use complete sentences with placeholders:
   ```python
   # Good
   _("You have {count} items in your cart.").format(count=item_count)
   
   # Avoid
   _("You have ") + str(item_count) + _(" items in your cart.")
   ```

4. **Handle Plurals Properly**: Different languages have different plural rules. Use the appropriate plural forms for each language.

5. **Test with Different Languages**: Always test your application with different languages to ensure that the translations work correctly and the UI adapts properly.

6. **Keep Translations Up to Date**: Regularly update your translation files as you add new features or change existing ones.

## Troubleshooting

### Translations Not Working

1. **Check if the translation file exists**: Make sure the .mo file exists in the correct location.
2. **Check if the language is available**: Make sure the language is in the list of available languages.
3. **Check if the message ID is correct**: Make sure the message ID in your code matches the one in the translation file.
4. **Check if the translation is loaded**: Use `translator.get_available_languages()` to see if the language is loaded.

### Adding Debug Logging

To debug translation issues, add logging to your code:

```python
import logging
from i18n import _, translator, language_detector

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def translate_message(message_id, user_id=None):
    language = language_detector.get_user_language(user_id)
    logger.debug(f"Translating message '{message_id}' for user {user_id} with language '{language}'")
    
    translated = _(message_id, user_id=user_id)
    logger.debug(f"Translated message: '{translated}'")
    
    return translated
```

## Conclusion

The internationalization system provides a flexible and powerful way to add multi-language support to the Dmarket Telegram Bot. By following these examples and best practices, you can create a user-friendly experience for users from different countries and language backgrounds.