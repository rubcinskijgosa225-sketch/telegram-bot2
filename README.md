# EscrowVault Python Bot

Telegram bot starter for EscrowVault, written in Python.

It uses only the Python standard library, so you can start without installing `aiogram` or other packages.

## Run

1. Create a bot in BotFather and copy the token.
2. Open `settings.py`.
3. Put your token into `BOT_TOKEN`.
4. Run:

```bash
python bot.py
```

If Windows says Python is not installed, install it from:

https://www.python.org/downloads/windows/

## Settings

Edit `settings.py`:

```python
BOT_TOKEN = "your_token_from_BotFather"
BOT_USERNAME = "YourBotUsername"
ESCROW_ACCOUNT = "@EscrowManager"
```

## Premium Telegram Emoji

Telegram premium/custom emoji are sent through `custom_emoji_id`.

To collect ids:

1. Start the bot.
2. Send `/emoji` to the bot.
3. Send a message containing the premium emoji you want.
4. Copy the `custom_emoji_id` values from the bot reply into `settings.py`.
