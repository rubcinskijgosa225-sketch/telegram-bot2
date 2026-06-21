import html
import json
import mimetypes
import os
import random
import re
import string
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.error import HTTPError
from pathlib import Path

try:
    import settings
except ImportError:
    settings = None


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
REQUISITES_FILE = DATA_DIR / "requisites.json"
ORDERS_FILE = DATA_DIR / "orders.json"
STATS_FILE = DATA_DIR / "stats.json"
BALANCES_FILE = DATA_DIR / "balances.json"
REQUESTS_FILE = DATA_DIR / "balance_requests.json"
ADMINS_FILE = DATA_DIR / "admins.json"
REFERRALS_FILE = DATA_DIR / "referrals.json"
USER_SETTINGS_FILE = DATA_DIR / "user_settings.json"

CONFIG = {}
SESSIONS = {}
CALLBACK_DEDUP = {}
OFFSET = 0
CURRENCIES = ("STARS", "TON", "USDT_TON", "RUB", "UAH", "USD", "BYN")
CALLBACK_DEDUP_SECONDS = 2.0

CURRENCY_EMOJI_IDS = {
    "STARS": ("5920101247708303325", "⭐"),
    "TON": ("5197515039296200279", "💰"),
    "RUB": ("5233426484923750391", "💵"),
    "USDT_TON": ("5253940223687013048", "💎"),
    "UAH": ("5399910841929709976", "🤑"),
    "USD": ("5213071887583692797", "💵"),
    "BYN": ("5296459459319575382", "💰"),
}

REQUISITE_EMOJI_IDS = {
    "title": ("5454134258580877567", "💳"),
    "usdt": ("5253940223687013048", "💎"),
    "ton": ("5197515039296200279", "💰"),
    "card": ("5233426484923750391", "💵"),
    "username": ("5920101247708303325", "⭐"),
    "send": ("5454068128969417666", "🔗"),
}

BUTTON_EMOJI_IDS = {
    "withdraw_balance": "5891105528356018797",
    "deposit_balance": "6037083366438737901",
    "menu": "5776288820467077551",
    "bind_usdt": "5904462880941545555",
    "bind_ton": "5776023601941582822",
    "bind_card_spb": "5769126056262898415",
    "bind_username": "5323333018151045958",
    "requisites": "5454134258580877567",
    "lang_ru": "5217591619108233553",
    "lang_en": "5434076031164103400",
    "check_balance": "5920332557466997677",
    "support": "5454068128969417666",
    "transfer_to_manager": "5453960484204083655",
    "rate_good": "5458872002645353776",
    "rate_bad": "5456602752379545711",
    "role_seller": "6037175527846975726",
    "role_buyer": "6032644646587338669",
    "product_nft_gift": "5397982951369622729",
    "product_nft_username": "5397982951369622729",
    "product_stars": "5920101247708303325",
    "product_ton": "5197515039296200279",
    "product_telegram_premium": "5453942819003591387",
    "currency_stars": "5920101247708303325",
    "currency_ton": "5197515039296200279",
    "currency_card_spb": "5233426484923750391",
    "currency_usdt_ton": "5253940223687013048",
    "currency_rub": "5233426484923750391",
    "currency_uah": "5399910841929709976",
    "currency_usd": "5213071887583692797",
    "currency_byn": "5296459459319575382",
    "share_order": "5458872002645353776",
    "cancel_order": "5454010941479873740",
}

ORDER_MESSAGE_EMOJI_IDS = {
    "created": ("5453942819003591387", "✈️"),
    "buyer": ("5470016867252855402", "🌐"),
    "amount": ("5246734896356936944", "📱"),
    "description": ("5454209184285356042", "🤝"),
    "link": ("5454068128969417666", "🔗"),
    "important": ("5260249805522744465", "🧿"),
    "verify": ("5458746443571421160", "⚡"),
    "owner": ("5433776470080107054", "🐶"),
    "success": ("5458872002645353776", "🤝"),
    "rating": ("5260343246831237239", "⚙️"),
    "buying": ("5454182246250474905", "🔥"),
    "price": ("5454134258580877567", "💳"),
    "pay_balance": ("5454010941479873740", "‼️"),
    "paid_amount": ("5402104393396931859", "⭐"),
    "paid_transfer": ("5453960484204083655", "❗"),
    "paid_after": ("5424912684078348533", "❤️"),
    "paid_warning": ("5454010941479873740", "‼️"),
    "paid_gift": ("5303400229549135579", "🎁"),
    "paid_remember": ("5453904641039298473", "🔓"),
    "connected_link": ("5454068128969417666", "🔗"),
    "connected_user": ("5454134554933619492", "👤"),
    "connected_success": ("5260343246831237239", "⚙️"),
    "connected_rating": ("5458866758490284496", "💖"),
    "profile_title": ("5454134554933619492", "👤"),
    "profile_username": ("5456367899272831797", "🕴"),
    "profile_id": ("5470016867252855402", "🌐"),
    "profile_rating": ("5260343246831237239", "⚙️"),
    "profile_success": ("5454068128969417666", "🔗"),
    "profile_requisites": ("5454134258580877567", "💳"),
    "balance_title": ("5454209184285356042", "☝️"),
    "balance_tag": ("5454102570312166471", "🌐"),
    "balance_requisites": ("5454134258580877567", "💳"),
    "balance_amount": ("5456122837028857707", "💲"),
    "balance_currency": ("5240428351063081133", "🌉"),
    "ref_link": ("5454068128969417666", "🔗"),
    "order_1": ("5794164805065514131", "1️⃣"),
    "order_2": ("5794085322400733645", "2️⃣"),
    "order_3": ("5794280000383358988", "3️⃣"),
    "order_4": ("5794241397217304511", "4️⃣"),
    "order_5": ("5793985348446984682", "5️⃣"),
    "security_title": ("5453904641039298473", "🔒"),
}


def custom_emoji(emoji_id, fallback):
    if not emoji_id:
        return html.escape(fallback)
    return f'<tg-emoji emoji-id="{html.escape(str(emoji_id))}">{html.escape(fallback)}</tg-emoji>'


def order_emoji(key):
    emoji_id, fallback = ORDER_MESSAGE_EMOJI_IDS.get(key, ("", ""))
    return custom_emoji(emoji_id, fallback)


def requisite_emoji(key):
    emoji_id, fallback = REQUISITE_EMOJI_IDS.get(key, ("", ""))
    return custom_emoji(emoji_id, fallback)


def currency_emoji(currency):
    emoji_id, fallback = CURRENCY_EMOJI_IDS.get(str(currency or "").upper(), ("", ""))
    return custom_emoji(emoji_id, fallback) if emoji_id else ""


def currency_label(currency, fiat=None):
    key = fiat if currency == "CARD_SPB" else currency
    shown = display_currency(currency, fiat)
    emoji = currency_emoji(key)
    return (emoji + " " if emoji else "") + html.escape(str(shown))


def price_text_html(amount, currency, fiat=None):
    return f"{html.escape(str(clean_amount(amount)))} {currency_label(currency, fiat)}"


def icon_button(text, icon_key, callback_data=None, url=None, style="primary"):
    button = {"text": text, "style": style}
    emoji_id = BUTTON_EMOJI_IDS.get(icon_key)
    if emoji_id:
        button["icon_custom_emoji_id"] = emoji_id
    if callback_data:
        button["callback_data"] = callback_data
    if url:
        button["url"] = url
    return button


def lang_for(chat_id=None, session=None):
    if session and session.get("lang"):
        return session.get("lang")
    if chat_id is not None:
        return get_user_language(chat_id) or "ru"
    return "ru"


def tr(chat_id, ru, en):
    return en if lang_for(chat_id) == "en" else ru


def tr_session(session, ru, en):
    return en if lang_for(session=session) == "en" else ru


def back_button(callback_data, text=None, style="primary", chat_id=None):
    text = text or tr(chat_id, "Назад", "Back")
    return icon_button(text, "menu", callback_data=callback_data, style=style)


def menu_button(callback_data="menu", chat_id=None):
    return icon_button(tr(chat_id, "В меню", "Menu"), "menu", callback_data=callback_data)


class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Bot is running")

    def log_message(self, format, *args):
        return


def start_render_health_server():
    port = os.environ.get("PORT")
    if not port:
        return

    server = HTTPServer(("0.0.0.0", int(port)), HealthCheckHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"Health check server is listening on port {port}.")


def main():
    global CONFIG

    CONFIG = load_env(BASE_DIR / ".env")
    token = CONFIG.get("BOT_TOKEN", "")

    if not token or "PUT_YOUR_TOKEN_HERE" in token:
        print("Set BOT_TOKEN in .env or settings.py first.")
        return

    reset_telegram_updates()
    start_render_health_server()
    print("EscrowVault Python bot is running.")
    run_long_polling()


def reset_telegram_updates():
    try:
        api("deleteWebhook", {"drop_pending_updates": True})
    except RuntimeError as error:
        print(f"Could not reset Telegram updates: {error}")


def run_long_polling():
    global OFFSET

    while True:
        try:
            updates = api("getUpdates", {
                "offset": OFFSET,
                "timeout": 30,
                "allowed_updates": ["message", "callback_query"],
            })

            for update in updates.get("result", []):
                OFFSET = update["update_id"] + 1
                handle_update(update)
        except KeyboardInterrupt:
            print("Bot stopped.")
            return
        except Exception as error:
            if "getUpdates HTTP 409" in str(error):
                print("Another bot instance is already polling this token. Stop the duplicate Railway/local process.")
                time.sleep(10)
                continue
            print(f"Error: {error}")
            time.sleep(2)


def handle_update(update):
    if "callback_query" in update:
        handle_callback(update["callback_query"])
        return

    message = update.get("message")
    if not message:
        return

    chat_id = message["chat"]["id"]
    user = message.get("from", {})
    text = (message.get("text") or "").strip()
    session = get_session(chat_id)
    remember_user(user)

    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        if len(parts) == 2:
            payload = parts[1].strip()
            if payload.startswith("ref="):
                register_referral(user, payload[4:])
            elif handle_order_link(message, payload):
                return

        saved_lang = get_user_language(chat_id)
        SESSIONS[chat_id] = {"lang": saved_lang, "step": "menu" if saved_lang else "language", "order": {}}
        if is_owner(user.get("id")):
            send_owner_start(chat_id)
        elif saved_lang:
            send_main_menu(chat_id, SESSIONS[chat_id])
        else:
            send_language_select(chat_id)
        return

    if handle_admin_command(message, text):
        return

    if session.get("step") == "collect_emoji":
        collect_emoji(message)
        return

    if text == "/emoji":
        session["step"] = "collect_emoji"
        send_text(chat_id, "⭐ Отправь мне сообщение с Telegram Premium emoji.\nЯ покажу custom_emoji_id, чтобы вставить их в дизайн бота.")
        return

    if text == "/testemoji":
        send_text(chat_id, welcome_text(), {"parse_mode": "HTML"})
        return

    if text == "/checkemoji":
        send_text(chat_id, emoji_diagnostic_text(), {"parse_mode": "HTML"})
        return

    if session.get("step") == "recipient_username":
        handle_recipient_input(message, session, text)
        return

    if session.get("step") == "order_amount":
        handle_amount_input(message, session, text)
        return

    if session.get("step") == "description":
        handle_description_input(message, session, text)
        return

    if session.get("step") == "bind_requisite":
        handle_requisite_input(message, session, text)
        return

    if session.get("step") == "balance_amount":
        handle_balance_amount(message, session, text)
        return

    send_text(chat_id, tr(chat_id, "Я не жду текст на этом шаге. Выберите действие кнопками ниже.", "I am not waiting for text at this step. Choose an action below."), {
        "parse_mode": "HTML",
        **back_keyboard("menu", chat_id),
    })


def handle_callback(query):
    chat_id = query["message"]["chat"]["id"]
    user = query.get("from", {})
    data = query.get("data", "")
    session = get_session(chat_id)
    remember_user(user)

    api("answerCallbackQuery", {"callback_query_id": query["id"]})
    if is_duplicate_callback(chat_id, user.get("id"), data):
        return

    if data == "owner_panel":
        if is_owner(user.get("id")):
            send_owner_start(chat_id)
        else:
            send_admin_panel(chat_id)
        return
    if data == "admin_panel":
        if is_admin_or_owner(user.get("id")):
            send_admin_panel(chat_id)
        else:
            send_access_denied(chat_id)
        return
    if data == "admin_commands":
        if is_admin_or_owner(user.get("id")):
            send_admin_commands(chat_id, is_owner(user.get("id")))
        else:
            send_access_denied(chat_id)
        return
    if data == "admin_balance_help":
        if is_admin_or_owner(user.get("id")):
            send_admin_balance_help(chat_id)
        else:
            send_access_denied(chat_id)
        return
    if data == "user_menu":
        session["step"] = "menu"
        send_main_menu(chat_id, session)
        return
    if data == "admin_manage" and is_owner(user.get("id")):
        send_admin_manage(chat_id)
        return
    if data.startswith("admin_remove:") and is_owner(user.get("id")):
        remove_admin(data.split(":", 1)[1])
        send_admin_manage(chat_id)
        return

    if data.startswith("pay:"):
        handle_pay_order(chat_id, user, data.split(":", 1)[1], by_admin=False)
        return
    if data.startswith("seller_transferred:"):
        handle_seller_transferred(chat_id, user, data.split(":", 1)[1])
        return
    if data.startswith("confirm_received:"):
        handle_confirm_received(chat_id, user, data.split(":", 1)[1])
        return
    if data.startswith("rate:"):
        handle_rate_user(chat_id, data)
        return

    if data in ("lang_ru", "lang_en"):
        session["lang"] = "ru" if data == "lang_ru" else "en"
        set_user_language(chat_id, session["lang"])
        session["step"] = "menu"
        send_welcome(chat_id, session)
        return

    if data == "menu":
        session["step"] = "menu"
        session["order"] = {}
        send_main_menu(chat_id, session)
        return
    if data == "language":
        session["step"] = "language"
        send_language_select(chat_id)
        return
    if data == "create_order":
        session["step"] = "role"
        session["order"] = {}
        send_role_select(chat_id)
        return
    if data.startswith("role:"):
        session["order"]["role"] = data.split(":", 1)[1]
        session["step"] = "product"
        send_product_select(chat_id, session)
        return
    if data.startswith("product:"):
        product = data.split(":", 1)[1]
        session["order"]["product"] = product
        if product == "card_spb":
            session["step"] = "fiat"
            send_fiat_select(chat_id, session, mode="order")
            return
        session["step"] = "currency"
        send_currency_select(chat_id, session, mode="order")
        return
    if data.startswith("fiat:"):
        session["order"]["fiat"] = data.split(":", 1)[1]
        session["order"]["currency"] = "CARD_SPB"
        if not has_requisites(chat_id, "CARD_SPB"):
            send_missing_requisites(chat_id, session)
            return
        ask_recipient(chat_id, session)
        return
    if data.startswith("currency:"):
        currency = data.split(":", 1)[1]
        session["order"]["currency"] = currency
        if not has_requisites(chat_id, currency):
            send_missing_requisites(chat_id, session)
            return
        ask_recipient(chat_id, session)
        return

    if data == "deposit_withdraw":
        send_balance_action_select(chat_id)
        return
    if data in ("balance_deposit", "balance_withdraw"):
        session["balance_action"] = "deposit" if data == "balance_deposit" else "withdraw"
        send_balance_currency_select(chat_id, session["balance_action"])
        return
    if data.startswith("balance_currency:"):
        _, action, currency = data.split(":", 2)
        session["balance_action"] = action
        session["balance_currency"] = currency
        if action == "withdraw" and not has_withdraw_requisites(chat_id, currency):
            send_text(chat_id, withdraw_missing_text(currency, chat_id), {
                "parse_mode": "HTML",
                "reply_markup": {
                    "inline_keyboard": [
                        [icon_button(tr(chat_id, "Реквизиты", "Requisites"), "requisites", callback_data="requisites")],
                        [back_button("deposit_withdraw")],
                    ]
                },
            })
            return
        session["step"] = "balance_amount"
        send_text(chat_id, tr(chat_id, "<b>Введите сумму.</b>", "<b>Enter the amount.</b>"), {
            "parse_mode": "HTML",
            **back_keyboard("deposit_withdraw", chat_id),
        })
        return

    if data == "profile":
        send_profile(chat_id, user)
        return
    if data == "check_balance":
        send_balance_list(chat_id)
        return
    if data == "referrals":
        send_referrals(chat_id, user)
        return
    if data == "my_orders":
        send_my_orders(chat_id, user)
        return
    if data == "requisites":
        session["step"] = "menu"
        session.pop("binding_key", None)
        send_requisites(chat_id)
        return
    if data.startswith("bind:"):
        send_bind_requisite(chat_id, session, data.split(":", 1)[1])
        return
    if data == "security":
        send_security(chat_id)
        return

    send_main_menu(chat_id, session)


def handle_admin_command(message, text):
    user = message.get("from", {})
    chat_id = message["chat"]["id"]
    parts = text.split()
    if not parts:
        return False

    command = parts[0].split("@", 1)[0].lower()
    if command in ("/id", "/myid"):
        send_text(chat_id, "".join([
            "<b>Ваш Telegram ID:</b>\n",
            f"<code>{html.escape(str(user.get('id')))}</code>\n\n",
            "Если это главный админ, добавьте в <code>settings.py</code>:\n",
            f"<code>OWNER_ID = \"{html.escape(str(user.get('id')))}\"</code>",
        ]), {"parse_mode": "HTML"})
        return True

    if command == "/admin":
        if is_owner(user.get("id")):
            send_owner_start(chat_id)
        elif is_admin(user.get("id")):
            send_admin_panel(chat_id)
        else:
            send_access_denied(chat_id)
        return True

    if command == "/vault" and len(parts) >= 2 and parts[1].lower() == "admin":
        if is_owner(user.get("id")):
            send_owner_start(chat_id)
        elif is_admin(user.get("id")):
            send_admin_panel(chat_id)
        else:
            send_access_denied(chat_id)
        return True

    if command == "/addadmin" and is_owner(user.get("id")):
        if len(parts) < 2:
            send_text(chat_id, "Формат: <code>/addadmin ID</code>", {"parse_mode": "HTML"})
            return True
        add_admin(parts[1])
        send_text(chat_id, f"Админ <code>{html.escape(parts[1])}</code> добавлен.", {"parse_mode": "HTML"})
        return True

    if command == "/deladmin" and is_owner(user.get("id")):
        if len(parts) < 2:
            send_text(chat_id, "Формат: <code>/deladmin ID</code>", {"parse_mode": "HTML"})
            return True
        remove_admin(parts[1])
        send_text(chat_id, f"Админ <code>{html.escape(parts[1])}</code> удалён.", {"parse_mode": "HTML"})
        return True

    if command == "/buy" and is_admin_or_owner(user.get("id")):
        if len(parts) < 2:
            send_text(chat_id, "Формат: <code>/buy тег_ордера</code>", {"parse_mode": "HTML"})
            return True
        handle_pay_order(chat_id, user, parts[1].lstrip("#"), by_admin=True)
        return True

    if command == "/success" and is_admin_or_owner(user.get("id")):
        if len(parts) < 3:
            send_text(chat_id, "Формат: <code>/success ID количество</code>", {"parse_mode": "HTML"})
            return True
        change_success(parts[1], int_amount(parts[2], default=0))
        send_text(chat_id, "Успешные ордеры обновлены.", {"parse_mode": "HTML"})
        return True

    if command == "/rating" and is_admin_or_owner(user.get("id")):
        if len(parts) < 3:
            send_text(chat_id, "Формат: <code>/rating ID оценка_1_5</code>", {"parse_mode": "HTML"})
            return True
        add_rating(parts[1], float_amount(parts[2], default=5.0))
        send_text(chat_id, "Рейтинг обновлен.", {"parse_mode": "HTML"})
        return True

    if command == "/addbalance" and is_admin_or_owner(user.get("id")):
        if len(parts) < 4:
            send_text(chat_id, "Формат: <code>/addbalance ID STARS 100</code>", {"parse_mode": "HTML"})
            return True
        add_balance(parts[1], parts[2].upper(), float_amount(parts[3], default=0))
        send_text(chat_id, "Баланс пополнен.", {"parse_mode": "HTML"})
        return True

    return False


def send_language_select(chat_id):
    send_text(chat_id, "<b>EscrowVault</b>\n\nВыберите язык / Choose language", {
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [[
                icon_button("Русский", "lang_ru", callback_data="lang_ru"),
                icon_button("English", "lang_en", callback_data="lang_en"),
            ]]
        },
    })


def send_welcome(chat_id, session):
    send_photo_or_text(chat_id, welcome_text(chat_id), main_menu_keyboard(chat_id))


def send_main_menu(chat_id, session):
    send_photo_or_text(chat_id, welcome_text(chat_id), main_menu_keyboard(chat_id))


def welcome_text(chat_id=None):
    if lang_for(chat_id) == "en":
        return "".join([
            "<b>EscrowVault</b>\n\n",
            quote_block("1", "Automated deals with NFTs and gifts."),
            quote_block("2", "Full protection for both sides."),
            quote_block("3", "Funds are locked until confirmation."),
            quote_block("4", f"Transfer through the manager: {escrow_account()}"),
            "\n",
            "<b>Choose an action below</b>",
        ])
    return "".join([
        "<b>EscrowVault</b>\n\n",
        quote_block("1", "Автоматические сделки с NFT и подарками."),
        quote_block("2", "Полная защита обеих сторон."),
        quote_block("3", "Средства заморожены до подтверждения."),
        quote_block("4", f"Передача через менеджера: {escrow_account()}"),
        "\n",
        "<b>Выберите действие ниже</b>",
    ])


def send_role_select(chat_id):
    send_text(chat_id, tr(chat_id, "<b>Создание ордера</b>\n\nВыберите, кто вы в сделке:", "<b>Create order</b>\n\nChoose your role in the deal:"), {
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [
                    icon_button(tr(chat_id, "Я продавец", "I am seller"), "role_seller", callback_data="role:seller"),
                    icon_button(tr(chat_id, "Я покупатель", "I am buyer"), "role_buyer", callback_data="role:buyer"),
                ],
                [back_button("menu", chat_id=chat_id)],
            ]
        },
    })


def send_product_select(chat_id, session):
    send_text(chat_id, tr(chat_id, "<b>В чем заключается ордер?</b>\n\nВыберите товар или услугу:", "<b>What is this order for?</b>\n\nChoose a product or service:"), {
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [
                    icon_button("NFT-Gift", "product_nft_gift", callback_data="product:nft_gift"),
                    icon_button("NFT-username", "product_nft_username", callback_data="product:nft_username"),
                ],
                [
                    icon_button("Stars", "product_stars", callback_data="product:stars"),
                    icon_button("TON", "product_ton", callback_data="product:ton"),
                ],
                [icon_button("Telegram Premium", "product_telegram_premium", callback_data="product:telegram_premium")],
                [back_button("create_order", chat_id=chat_id)],
            ]
        },
    })


def send_currency_select(chat_id, session, mode):
    callback_prefix = "balance_currency:" + session.get("balance_action", "deposit") + ":" if mode == "balance" else "currency:"
    send_text(chat_id, tr(chat_id, "<b>Выберите валюту оплаты</b>\n\nПосле выбора валюты укажите получателя и сумму.", "<b>Choose payment currency</b>\n\nAfter choosing a currency, enter the recipient and amount."), {
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [
                    icon_button(tr(chat_id, "Звезды", "Stars"), "currency_stars", callback_data=callback_prefix + "STARS", style="success"),
                    icon_button("TON", "currency_ton", callback_data=callback_prefix + "TON"),
                ],
                [
                    icon_button(tr(chat_id, "Карта/СПБ", "Card/SBP"), "currency_card_spb", callback_data="product:card_spb" if mode == "order" else callback_prefix + "RUB"),
                    icon_button("USDT (TON)", "currency_usdt_ton", callback_data=callback_prefix + "USDT_TON", style="success"),
                ],
                [back_button("role:" + session.get("order", {}).get("role", "seller") if mode == "order" else "deposit_withdraw", chat_id=chat_id)],
            ]
        },
    })


def send_fiat_select(chat_id, session, mode):
    action = session.get("balance_action", "deposit")
    prefix = "fiat:" if mode == "order" else f"balance_currency:{action}:"
    back = "product:" + session.get("order", {}).get("product", "nft_gift") if mode == "order" else "deposit_withdraw"
    send_text(chat_id, tr(chat_id, "<b>Карта / СПБ</b>\n\nВыберите валюту карты:", "<b>Card / SBP</b>\n\nChoose card currency:"), {
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [
                    icon_button("RUB", "currency_rub", callback_data=prefix + "RUB"),
                    icon_button("UAH", "currency_uah", callback_data=prefix + "UAH"),
                ],
                [
                    icon_button("USD", "currency_usd", callback_data=prefix + "USD"),
                    icon_button("BYN", "currency_byn", callback_data=prefix + "BYN"),
                ],
                [back_button(back, chat_id=chat_id)],
            ]
        },
    })


def ask_recipient(chat_id, session):
    session["step"] = "recipient_username"
    order = session["order"]
    text = "".join([
        f"<b>{recipient_title(order.get('product'))}</b>\n\n",
        tr(chat_id, "Укажите <code>@username</code> получателя\n\n", "Enter the recipient <code>@username</code>\n\n"),
        quote_block("⭐", min_text(order.get("currency"), order.get("fiat"), chat_id)),
    ])
    send_text(chat_id, text, {"parse_mode": "HTML", **back_keyboard("menu", chat_id)})


def handle_recipient_input(message, session, text):
    chat_id = message["chat"]["id"]
    if not is_username(text):
        send_text(chat_id, tr(chat_id, "<b>Неверный @username.</b>\n\nУкажите username в формате <code>@username</code>.", "<b>Invalid @username.</b>\n\nEnter username in this format: <code>@username</code>."), {
            "parse_mode": "HTML",
            **back_keyboard("menu", chat_id),
        })
        return

    session["order"]["recipient"] = text
    session["step"] = "order_amount"
    send_text(chat_id, tr(chat_id, "<b>Введите количество валюты.</b>", "<b>Enter the currency amount.</b>"), {
        "parse_mode": "HTML",
        **back_keyboard("menu", chat_id),
    })


def handle_amount_input(message, session, text):
    chat_id = message["chat"]["id"]
    amount = float_amount(text, default=0)
    if amount <= 0:
        send_text(chat_id, tr(chat_id, "<b>Введите сумму числом.</b>", "<b>Enter the amount as a number.</b>"), {
            "parse_mode": "HTML",
            **back_keyboard("menu", chat_id),
        })
        return

    session["order"]["amount"] = clean_amount(amount)
    session["step"] = "description"
    product = session["order"].get("product")
    examples = {
        "nft_gift": tr(chat_id, "Пример: https://t.me/nft/pepe", "Example: https://t.me/nft/pepe"),
        "nft_username": tr(chat_id, "Пример: https://t.me/nft/example", "Example: https://t.me/nft/example"),
        "stars": tr(chat_id, "Пример: 1000 звезд на @username", "Example: 1000 Stars to @username"),
        "ton": tr(chat_id, "Пример: 5 TON на указанный TON-адрес", "Example: 5 TON to the specified TON address"),
        "telegram_premium": tr(chat_id, "Пример: Telegram Premium на 3 месяца", "Example: Telegram Premium for 3 months"),
    }
    example = examples.get(product, tr(chat_id, "Пример: описание товара или услуги", "Example: product or service description"))

    send_text(chat_id, "".join([
        tr(chat_id, "<b>Описание товара</b>\n\n", "<b>Product description</b>\n\n"),
        f"<i>{html.escape(example)}</i>",
    ]), {
        "parse_mode": "HTML",
        **back_keyboard("menu", chat_id),
    })


def is_nft_link(value):
    parsed = urllib.parse.urlparse(str(value).strip())
    return parsed.scheme == "https" and parsed.netloc.lower() == "t.me" and parsed.path.lower().startswith("/nft/") and len(parsed.path.strip("/")) > 4


def product_description_example(product):
    examples = {
        "nft_gift": "https://t.me/nft/pepe",
        "nft_username": "https://t.me/nft/example",
        "stars": "1000 Stars to @username",
        "ton": "5 TON на указанный TON-адрес",
        "telegram_premium": "Telegram Premium for 3 months",
    }
    return examples.get(product, "описание товара или услуги")


def is_valid_product_description(product, value):
    text = str(value or "").strip()
    lowered = text.lower()
    if product in ("nft_gift", "nft_username"):
        return is_nft_link(text)
    if product == "stars":
        return bool(re.search(r"\d", text)) and ("звезд" in lowered or "stars" in lowered or "⭐" in text) and "@" in text
    if product == "ton":
        return bool(re.search(r"\d", text)) and "ton" in lowered
    if product == "telegram_premium":
        return "premium" in lowered and bool(re.search(r"\d", text))
    return len(text) >= 3


def handle_description_input(message, session, text):
    chat_id = message["chat"]["id"]
    order = session["order"]
    product = order.get("product")
    if not is_valid_product_description(product, text):
        example = product_description_example(product)
        send_text(chat_id, tr(chat_id, f"<b>Неправильный ввод.</b>\n\nОтправьте описание в формате:\n<code>{html.escape(example)}</code>", f"<b>Invalid input.</b>\n\nSend the description in this format:\n<code>{html.escape(example)}</code>"), {
            "parse_mode": "HTML",
            **back_keyboard("menu", chat_id),
        })
        return

    session["order"]["description"] = text
    session["step"] = "menu"

    order_id = make_order_id()
    creator = user_snapshot(message.get("from", {}))
    role = order.get("role")
    seller = creator if role == "seller" else None
    buyer = creator if role == "buyer" else None
    currency = display_currency(order.get("currency"), order.get("fiat"))
    bot_username = CONFIG.get("BOT_USERNAME", "EscrowVaultBot").lstrip("@")
    link = f"https://t.me/{bot_username}?start={order_id}"

    saved_order = {
        "id": order_id,
        "creator_chat_id": chat_id,
        "creator_role": role,
        "seller": seller,
        "buyer": buyer,
        "recipient": order.get("recipient"),
        "product": order.get("product"),
        "currency": order.get("currency"),
        "fiat": order.get("fiat"),
        "amount": order.get("amount"),
        "description": text,
        "status": "created",
        "created_at": int(time.time()),
    }
    save_order(saved_order)
    log_owner(f"🆕 Создан ордер #{order_id}\nСоздатель: {format_user_short(creator)}\nТовар: {text}\nСумма: {price_text(order.get('amount'), currency)}")

    text_out = "".join([
        f"{order_emoji('created')} {tr(chat_id, 'ордер создан', 'order created')}: <code>{html.escape(order_id)}</code>\n\n",
        f"{order_emoji('buyer')} {tr(chat_id, 'username покупателя', 'buyer username')}: {html.escape(order.get('recipient') or tr(chat_id, 'не указан', 'not specified'))}\n",
        f"{order_emoji('amount')} <b>{tr(chat_id, 'Сумма', 'Amount')}:</b> {price_text_html(order.get('amount'), order.get('currency'), order.get('fiat'))}\n",
        f"{order_emoji('description')} <b>{tr(chat_id, 'Описание', 'Description')}:</b> {html.escape(text)}\n\n",
        f"{order_emoji('link')} <b>{tr(chat_id, 'Ссылка для покупателя', 'Link for the buyer')}:</b>\n\n",
        f"{html.escape(link)}\n\n",
        "<blockquote>",
        f"{order_emoji('important')} <i>{tr(chat_id, 'Важно: передача подарка выполняется через менеджера', 'Important: the gift transfer is handled through the manager')}\n{html.escape(escrow_account())}</i>\n",
        f"{order_emoji('verify')} <b>{tr(chat_id, 'Обязательно сверяйте тег ордера!', 'Always verify the order tag!')}</b>",
        "</blockquote>",
    ])

    send_text(chat_id, text_out, {
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [icon_button(tr(chat_id, "Поделиться ордером", "Share order"), "share_order", url="https://t.me/share/url?" + urllib.parse.urlencode({"url": link}))],
                [icon_button(tr(chat_id, "Тех. Поддержка", "Support"), "support", url=support_url())],
                [icon_button(tr(chat_id, "Отменить ордер", "Cancel order"), "cancel_order", callback_data="menu", style="danger")],
            ]
        },
    })


def handle_order_link(message, order_id):
    order = get_order(order_id)
    if not order:
        return False

    chat_id = message["chat"]["id"]
    user = user_snapshot(message.get("from", {}))

    if str(order.get("creator_chat_id")) == str(chat_id):
        send_text(chat_id, tr(chat_id, "<b>Нельзя оплатить свой ордер.</b>\n\nОтправьте ссылку покупателю, чтобы он подключился к сделке.", "<b>You cannot pay your own order.</b>\n\nSend the link to the buyer so they can join the deal."), {
            "parse_mode": "HTML",
            **back_keyboard("menu", chat_id),
        })
        return True

    if order.get("creator_role") == "seller":
        if not order.get("buyer"):
            order["buyer"] = user
        connected_user = order["buyer"]
        connected_role = tr(order.get("creator_chat_id"), "покупатель", "buyer")
    else:
        if not order.get("seller"):
            order["seller"] = user
        connected_user = order["seller"]
        connected_role = tr(order.get("creator_chat_id"), "продавец", "seller")

    if order.get("status") == "created":
        order["status"] = "connected"
    save_order(order)

    send_text(chat_id, buyer_order_text(order, message.get("text") or "/start", chat_id), {
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [{"text": tr(chat_id, "Оплатить", "Pay"), "callback_data": f"pay:{order_id}", "style": "success"}],
                [menu_button(chat_id=chat_id)],
            ]
        },
    })

    creator_chat_id = order.get("creator_chat_id")
    if creator_chat_id and creator_chat_id != chat_id:
        stats = get_user_stats(connected_user.get("id"))
        send_text(creator_chat_id, "".join([
            f"{order_emoji('connected_link')} {tr(creator_chat_id, 'К ордеру', 'The order')} <code>#{html.escape(order_id)}</code>\n",
            f"{tr(creator_chat_id, 'подключился', 'was joined by')} {connected_role}.\n\n",
            f"{order_emoji('connected_user')} {html.escape(format_user_short(connected_user))} (ID <code>{html.escape(str(connected_user.get('id')))}</code>)\n\n",
            f"{order_emoji('connected_success')} {tr(creator_chat_id, 'Успешные ордера', 'Successful orders')}: <b>{stats['successful_orders']}</b>\n\n",
            f"{order_emoji('connected_rating')} <b>{tr(creator_chat_id, 'Рейтинг', 'Rating')}: {html.escape(format_rating(stats))} {tr(creator_chat_id, 'за все время', 'overall')}.</b>",
        ]), {
            "parse_mode": "HTML",
            **back_keyboard("menu", chat_id),
        })

    return True


def handle_pay_order(chat_id, user, order_id, by_admin=False):
    order = get_order(order_id)
    if not order:
        send_text(chat_id, tr(chat_id, "Ордер не найден.", "Order not found."))
        return

    amount = float_amount(str(order.get("amount")), default=0)
    currency_key = balance_currency_key(order)
    payer = order.get("buyer") if order.get("creator_role") == "seller" else order.get("seller")
    payer_id = str((payer or {}).get("id") or user.get("id"))

    if not by_admin and get_balance(payer_id, currency_key) < amount:
        send_text(chat_id, "".join([
            tr(chat_id, "<b>Недостаточно средств для оплаты.</b>\n\n", "<b>Not enough funds to pay.</b>\n\n"),
            tr(chat_id, "Пополните баланс через менеджера и повторите оплату.", "Top up your balance through the manager and try again."),
        ]), {
            "parse_mode": "HTML",
            "reply_markup": {
                "inline_keyboard": [
                    [icon_button(tr(chat_id, "Пополнить баланс", "Top up balance"), "deposit_balance", callback_data="balance_deposit", style="success")],
                    [{"text": tr(chat_id, "Менеджер", "Manager"), "url": manager_url(), "style": "primary"}],
                    [menu_button(chat_id=chat_id)],
                ]
            },
        })
        return

    if not by_admin:
        add_balance(payer_id, currency_key, -amount)

    order["status"] = "paid"
    order["paid_at"] = int(time.time())
    save_order(order)
    log_owner(f"💳 Оплачен ордер #{order_id}\nПлательщик: {format_user_short(user_snapshot(user))}\nТовар: {order.get('description')}\nСумма: {price_text(order.get('amount'), display_currency(order.get('currency'), order.get('fiat')))}")

    send_text(chat_id, "".join([
        quote_block("⭐", tr(chat_id, f"{price_text(order.get('amount'), display_currency(order.get('currency'), order.get('fiat')))} успешно списано с вашего баланса", f"{price_text(order.get('amount'), display_currency(order.get('currency'), order.get('fiat')))} has been debited from your balance")),
        "\n",
        quote_block(tr(chat_id, "Ордер", "Order"), tr(chat_id, f"#{order_id} оплачен", f"#{order_id} paid")),
        "\n",
        tr(chat_id, "Оплата по ордеру учтена.", "The order payment has been recorded."),
    ]), {
        "parse_mode": "HTML",
        **back_keyboard("menu", chat_id),
    })

    seller_chat_id = user_chat_id(order.get("seller"))
    if not seller_chat_id and order.get("creator_role") == "seller":
        seller_chat_id = order.get("creator_chat_id")
    if seller_chat_id:
        send_text(seller_chat_id, seller_paid_text(order, seller_chat_id), {
            "parse_mode": "HTML",
            "reply_markup": {
                "inline_keyboard": [
                    [icon_button(tr(seller_chat_id, "Я передал менеджеру", "I transferred to the manager"), "transfer_to_manager", callback_data=f"seller_transferred:{order_id}", style="success")],
                    [icon_button(tr(seller_chat_id, "Менеджер", "Manager"), "support", url=manager_url(), style="primary")],
                ]
            },
        })


def handle_seller_transferred(chat_id, user, order_id):
    order = get_order(order_id)
    if not order:
        send_text(chat_id, tr(chat_id, "Ордер не найден.", "Order not found."))
        return

    order["status"] = "transferred"
    save_order(order)

    send_text(chat_id, "".join([
        quote_block("✅", f"Передача по ордеру #{order_id} отмечена"),
        "\n",
        tr(chat_id, "<i>Ожидаем подтверждение покупателя.</i>", "<i>Waiting for buyer confirmation.</i>"),
    ]), {
        "parse_mode": "HTML",
        **back_keyboard("menu", chat_id),
    })

    buyer_chat_id = user_chat_id(order.get("buyer"))
    if buyer_chat_id:
        send_text(buyer_chat_id, "".join([
            quote_block("🎁", tr(buyer_chat_id, "Продавец сообщил о передаче в эскроу", "The seller reported the transfer to escrow")),
            "\n",
            quote_block("Ордер", f"#{order_id}"),
            "\n",
            quote_block("", tr(buyer_chat_id, "Как получите — подтвердите", "Confirm once you receive it")),
        ]), {
            "parse_mode": "HTML",
            "reply_markup": {
                "inline_keyboard": [
                    [{"text": tr(buyer_chat_id, "Подтвердить получение", "Confirm receipt"), "callback_data": f"confirm_received:{order_id}", "style": "success"}],
                    [menu_button(chat_id=buyer_chat_id)],
                ]
            },
        })


def handle_confirm_received(chat_id, user, order_id):
    order = get_order(order_id)
    if not order:
        send_text(chat_id, tr(chat_id, "Ордер не найден.", "Order not found."))
        return

    order["status"] = "completed"
    order["completed_at"] = int(time.time())
    save_order(order)
    increment_success(order.get("seller"))
    increment_success(order.get("buyer"))
    log_owner(f"✅ Завершен ордер #{order_id}\nТовар: {order.get('description')}")

    send_text(chat_id, "".join([
        "<blockquote>",
        tr(chat_id, "✅ <b>Спасибо! Получение подтверждено</b>", "✅ <b>Thank you! Receipt confirmed</b>"),
        "</blockquote>\n",
        f"{order_emoji('created')} <i>{tr(chat_id, 'Ордер', 'Order')} <code>#{html.escape(order_id)}</code> {tr(chat_id, 'завершён', 'completed')}</i>\n\n",
        f"{order_emoji('success')} <b>{tr(chat_id, 'Благодарим за использование нашего сервиса!', 'Thank you for using our service!')}</b>",
    ]), {
        "parse_mode": "HTML",
        **back_keyboard("menu", chat_id),
    })

    seller_chat_id = user_chat_id(order.get("seller"))
    buyer = order.get("buyer") or {}
    if seller_chat_id and seller_chat_id != chat_id:
        send_text(seller_chat_id, "".join([
            f"{order_emoji('created')} <i>{tr(seller_chat_id, 'Ордер', 'Order')} <code>#{html.escape(order_id)}</code> {tr(seller_chat_id, 'завершён', 'completed')}</i>\n\n",
            f"{order_emoji('owner')} <b>{tr(seller_chat_id, 'Устроила ли вас сделка с пользователем', 'Were you satisfied with the deal with')} {html.escape(format_user_short(buyer))}?</b>\n\n",
            tr(seller_chat_id, "Ответ повлияет на рейтинг пользователя.\nБлагодарим за использование нашего сервиса.", "Your answer will affect the user's rating.\nThank you for using our service."),
        ]), {
            "parse_mode": "HTML",
            "reply_markup": {
                "inline_keyboard": [
                    [icon_button(tr(seller_chat_id, "Все прошло отлично", "Everything went well"), "rate_good", callback_data=f"rate:{order_id}:{buyer.get('id')}:5", style="success")],
                    [icon_button(tr(seller_chat_id, "Были проблемы", "There were problems"), "rate_bad", callback_data=f"rate:{order_id}:{buyer.get('id')}:1", style="danger")],
                ]
            },
        })


def handle_rate_user(chat_id, data):
    _, order_id, user_id, score = data.split(":", 3)
    order = get_order(order_id)
    if not order:
        send_text(chat_id, tr(chat_id, "Ордер не найден.", "Order not found."))
        return

    rated_key = f"rated_{user_id}"
    if order.get(rated_key):
        send_text(chat_id, tr(chat_id, "Оценка по этому ордеру уже учтена.", "The rating for this order has already been recorded."), {"parse_mode": "HTML", **back_keyboard("menu", chat_id)})
        return

    add_rating(user_id, float_amount(score, default=5))
    order[rated_key] = True
    save_order(order)
    send_text(chat_id, tr(chat_id, "Спасибо, оценка учтена.", "Thank you, the rating has been recorded."), {"parse_mode": "HTML", **back_keyboard("menu", chat_id)})


def buyer_order_text(order, start_text, chat_id=None):
    seller = order.get("seller") or {}
    stats = get_user_stats(seller.get("id"))
    return "".join([
        f"{order_emoji('created')} {tr(chat_id, 'ордер', 'order')}: <code>{html.escape(order['id'])}</code>\n\n",
        f"{order_emoji('owner')} {tr(chat_id, 'Владелец ордера', 'Order owner')}: {html.escape(format_user_short(seller))}\n\n",
        f"{order_emoji('success')} {tr(chat_id, 'Успешные ордера', 'Successful orders')}: <b>{stats['successful_orders']}</b>\n\n",
        f"{order_emoji('rating')} {tr(chat_id, 'Рейтинг', 'Rating')}: <b>{html.escape(format_rating(stats))}</b>\n\n",
        f"{order_emoji('buying')} {tr(chat_id, 'Вы покупаете', 'You are buying')}: {html.escape(order.get('description', tr(chat_id, 'Описание товара', 'Product description')))}\n\n",
        f"{order_emoji('price')} {tr(chat_id, 'Цена', 'Price')}: <b>{price_text_html(order.get('amount'), order.get('currency'), order.get('fiat'))}</b>\n\n",
        "<blockquote>",
        f"{order_emoji('pay_balance')} {tr(chat_id, 'Оплата происходит из баланса', 'Payment is made from the balance')} {currency_label(balance_currency_key(order), order.get('fiat'))}",
        "</blockquote>",
    ])

def seller_paid_text(order, chat_id=None):
    manager = escrow_account()
    return "".join([
        f"{order_emoji('created')} {tr(chat_id, 'Ордер', 'Order')} <code>#{html.escape(order['id'])}</code> {tr(chat_id, 'успешно оплачен', 'has been paid')}\n\n",
        f"{order_emoji('paid_amount')} {tr(chat_id, 'Сумма', 'Amount')}: <b>{price_text_html(order.get('amount'), order.get('currency'), order.get('fiat'))}</b>\n\n",
        f"{order_emoji('paid_transfer')} {tr(chat_id, 'Передавайте подарок менеджеру', 'Transfer the gift to the manager')}: {html.escape(manager)}\n\n",
        f"{order_emoji('paid_after')} {tr(chat_id, 'После передачи нажмите кнопку в боте', 'After the transfer, press the button in the bot')}\n\n",
        "<blockquote>",
        f"{order_emoji('paid_warning')} <b>{tr(chat_id, 'ВНИМАНИЕ! ВАЖНАЯ ИНФОРМАЦИЯ О БЕЗОПАСНОСТИ', 'ATTENTION! IMPORTANT SAFETY INFORMATION')}</b>\n",
        f"{order_emoji('paid_gift')} {tr(chat_id, 'Участились случаи мошенничества! Передавайте товар исключительно менеджеру сервиса.', 'Fraud cases have increased! Transfer the item only to the service manager.')}\n",
        tr(chat_id, "При передаче товара напрямую пользователю вы останетесь без своих средств.", "If you transfer the item directly to the user, you may lose your funds."),
        "</blockquote>\n",
        "<blockquote>",
        f"{order_emoji('paid_remember')} <b>{tr(chat_id, 'Помните', 'Remember')}:</b> {tr(chat_id, 'Только', 'Only')} {html.escape(manager)} {tr(chat_id, 'гарантирует безопасность ордера', 'guarantees order safety')}!",
        "</blockquote>",
    ])

def send_balance_action_select(chat_id):
    send_text(chat_id, tr(chat_id, "<b>Выберите подходящий вариант использования</b>", "<b>Choose an action</b>"), {
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [[
                icon_button(tr(chat_id, "Вывести баланс", "Withdraw"), "withdraw_balance", callback_data="balance_withdraw"),
                icon_button(tr(chat_id, "Пополнить баланс", "Deposit"), "deposit_balance", callback_data="balance_deposit", style="success"),
            ], [menu_button(chat_id=chat_id)]]
        },
    })


def send_balance_currency_select(chat_id, action):
    title = tr(chat_id, "Выберите валюту для пополнения баланса", "Choose a currency to deposit") if action == "deposit" else tr(chat_id, "Выберите валюту для вывода баланса", "Choose a currency to withdraw")
    prefix = f"balance_currency:{action}:"
    send_text(chat_id, f"<b>{title}</b>", {
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [
                    icon_button(tr(chat_id, "Звезды", "Stars"), "currency_stars", callback_data=prefix + "STARS", style="success"),
                    icon_button("TON", "currency_ton", callback_data=prefix + "TON"),
                ],
                [
                    icon_button("RUB", "currency_rub", callback_data=prefix + "RUB"),
                    icon_button("USDT (TON)", "currency_usdt_ton", callback_data=prefix + "USDT_TON", style="success"),
                ],
                [
                    icon_button("UAH", "currency_uah", callback_data=prefix + "UAH"),
                    icon_button("USD", "currency_usd", callback_data=prefix + "USD"),
                    icon_button("BYN", "currency_byn", callback_data=prefix + "BYN"),
                ],
                [back_button("deposit_withdraw", chat_id=chat_id)],
            ]
        },
    })


def handle_balance_amount(message, session, text):
    chat_id = message["chat"]["id"]
    amount = float_amount(text, default=0)
    action = session.get("balance_action")
    currency = session.get("balance_currency")
    if amount <= 0:
        send_text(chat_id, tr(chat_id, "Ошибка, введите правильную сумму.", "Error, enter a valid amount."), {"parse_mode": "HTML", **back_keyboard("deposit_withdraw", chat_id)})
        return

    if action == "withdraw":
        if get_balance(chat_id, currency) < amount:
            send_text(chat_id, tr(chat_id, "Ошибка вывода, введите правильную сумму.", "Withdrawal error, enter a valid amount."), {"parse_mode": "HTML", **back_keyboard("deposit_withdraw", chat_id)})
            return
        add_balance(chat_id, currency, -amount)

    request_id = make_request_id()
    save_balance_request({
        "id": request_id,
        "user": user_snapshot(message.get("from", {})),
        "action": action,
        "currency": currency,
        "amount": clean_amount(amount),
        "created_at": int(time.time()),
    })
    session["step"] = "menu"

    if action == "deposit":
        send_text(chat_id, "".join([
            f"{order_emoji('balance_title')} <b>{tr(chat_id, 'Пополнение баланса', 'Balance deposit')}</b>\n\n",
            f"{order_emoji('balance_tag')} <b>{tr(chat_id, 'Тег запроса', 'Request tag')}:</b> {html.escape(request_id)}\n\n",
            f"{order_emoji('balance_requisites')} <b>{tr(chat_id, 'Реквизиты', 'Requisites')}:</b> {html.escape(manager_requisites(currency))}\n\n",
            f"{order_emoji('balance_amount')} <b>{tr(chat_id, 'Сумма', 'Amount')}:</b> {html.escape(str(clean_amount(amount)))}\n\n",
            f"{order_emoji('balance_currency')} <b>{tr(chat_id, 'Валюта', 'Currency')}:</b> {currency_label(currency, currency)}\n\n",
            tr(chat_id, "<i>Предоставьте тег запроса нашему менеджеру, для пополнения баланса.</i>", "<i>Send this request tag to our manager to top up your balance.</i>"),
        ]), {
            "parse_mode": "HTML",
            "reply_markup": {
                "inline_keyboard": [
                    [icon_button(tr(chat_id, "Менеджер", "Manager"), "support", url=manager_url(), style="success")],
                    [back_button("deposit_withdraw", chat_id=chat_id)],
                ]
            },
        })
    else:
        send_text(chat_id, "".join([
            f"{order_emoji('balance_title')} <b>{tr(chat_id, 'Вывод баланса', 'Balance withdrawal')}</b>\n\n",
            f"{order_emoji('balance_tag')} <b>{tr(chat_id, 'Тег запроса', 'Request tag')}:</b> {html.escape(request_id)}\n\n",
            f"{order_emoji('balance_requisites')} <b>{tr(chat_id, 'Реквизиты', 'Requisites')}:</b> {html.escape(withdraw_requisites(chat_id, currency) or tr(chat_id, 'не указаны', 'not specified'))}\n\n",
            f"{order_emoji('balance_amount')} <b>{tr(chat_id, 'Сумма', 'Amount')}:</b> {html.escape(str(clean_amount(amount)))}\n\n",
            f"{order_emoji('balance_currency')} <b>{tr(chat_id, 'Валюта', 'Currency')}:</b> {currency_label(currency, currency)}\n\n",
            tr(chat_id, "<i>Ожидайте вывод средств в течение 2-5 минут, при сильной нагрузке на сервис, время может отличаться.</i>", "<i>Withdrawal usually takes 2-5 minutes. During high load, it may take longer.</i>"),
        ]), {
            "parse_mode": "HTML",
            **back_keyboard("deposit_withdraw", chat_id),
        })


def send_profile(chat_id, user):
    stats = get_user_stats(user.get("id"))
    requisites = get_user_requisites(chat_id)
    text = "".join([
        f"<b>{tr(chat_id, 'Профиль', 'Profile')}</b>\n\n",
        quote_block("👤", f"{tr(chat_id, 'Юзернейм', 'Username')}: {username(user)}"),
        quote_block("🆔", f"{tr(chat_id, 'Айди пользователя', 'User ID')}: {user.get('id')}"),
        quote_block("⭐", f"{tr(chat_id, 'Рейтинг', 'Rating')}: {format_rating(stats)}"),
        quote_block("📈", f"{tr(chat_id, 'Успешных ордеров', 'Successful orders')}: {stats['successful_orders']}"),
        quote_block("💳", f"{tr(chat_id, 'Реквизиты', 'Requisites')}: {requisites_status(requisites, chat_id)}"),
    ])
    send_text(chat_id, text, {
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [icon_button(tr(chat_id, "Проверить баланс", "Check balance"), "check_balance", callback_data="check_balance", style="success")],
                [menu_button(chat_id=chat_id)],
            ]
        },
    })


def send_balance_list(chat_id):
    balances = get_balances(chat_id)
    labels = {
        "STARS": tr(chat_id, "звезд", "Stars"),
        "TON": "TON",
        "USDT_TON": "USDT (TON)",
        "RUB": "RUB",
        "UAH": "UAH",
        "USD": "USD",
        "BYN": "BYN",
    }
    lines = [f"<b>{tr(chat_id, 'Ваш баланс', 'Your balance')}:</b>", ""]
    for currency in CURRENCIES:
        lines.append(f"{currency_emoji(currency)} {html.escape(labels[currency])}: {html.escape(str(clean_amount(balances.get(currency, 0))))}")
    send_text(chat_id, "\n".join(lines), {"parse_mode": "HTML", **back_keyboard("profile", chat_id)})


def send_referrals(chat_id, user):
    bot_username = CONFIG.get("BOT_USERNAME", "EscrowVaultBot").lstrip("@")
    code = referral_code(user.get("id"))
    data = load_json(REFERRALS_FILE, {})
    invited = data.get("invited", {}).get(str(user.get("id")), [])
    text = "".join([
        f"{order_emoji('ref_link')} <b>Ваша реферальная ссылка</b>\n\n",
        f"https://t.me/{html.escape(bot_username)}?start=ref={html.escape(code)}\n\n",
        "<blockquote>",
        f"• Рефералы: {len(invited)}\n",
        "• Заработано: 0.0 TON\n",
        "• Доля: 40% от комиссии сервиса",
        "</blockquote>",
    ])
    send_photo_or_text(chat_id, text, back_keyboard("menu", chat_id))


def send_my_orders(chat_id, user):
    orders = list(load_json(ORDERS_FILE, {}).values())
    user_id = user.get("id")
    owned = [
        order for order in orders
        if (order.get("seller") or {}).get("id") == user_id or (order.get("buyer") or {}).get("id") == user_id
    ]
    owned.sort(key=lambda order: order.get("created_at", 0), reverse=True)
    if not owned:
        send_text(chat_id, tr(chat_id, "<b>У вас пока нет ордеров.</b>", "<b>You do not have any orders yet.</b>"), {"parse_mode": "HTML", **back_keyboard("menu", chat_id)})
        return

    lines = [f"<b>{tr(chat_id, 'Последние 5 ордеров', 'Last 5 orders')}:</b>\n"]
    for index, order in enumerate(owned[:5], start=1):
        currency = display_currency(order.get("currency"), order.get("fiat"))
        lines.append(f"{order_emoji('order_' + str(index))} <code>#{html.escape(order['id'])}</code> — <b>{html.escape(price_text(order.get('amount'), currency))}</b>")
    send_text(chat_id, "\n".join(lines), {"parse_mode": "HTML", **back_keyboard("menu", chat_id)})

def shown_requisite(value, chat_id=None):
    return html.escape(value) if value else tr(chat_id, "не указана", "not specified")


def send_requisites(chat_id):
    requisites = get_user_requisites(chat_id)
    usdt = requisites.get("usdt_ton_address") or CONFIG.get("USDT_TON_ADDRESS")
    ton = requisites.get("ton_address") or CONFIG.get("TON_ADDRESS")
    card = requisites.get("card_spb_requisites") or CONFIG.get("CARD_SPB_REQUISITES")
    stars = requisites.get("stars_receiver") or CONFIG.get("STARS_RECEIVER")
    text = "".join([
        f"{requisite_emoji('title')} <b>{tr(chat_id, 'Ваши текущие реквизиты', 'Your current requisites')}:</b>\n\n",
        f"{requisite_emoji('usdt')} <b>USDT (TON):</b>\n{shown_requisite(usdt, chat_id)}\n\n",
        f"{requisite_emoji('ton')} <b>TON:</b>\n{shown_requisite(ton, chat_id)}\n\n",
        f"{requisite_emoji('card')} <b>{tr(chat_id, 'Карта/СПБ', 'Card/SBP')}:</b>\n{shown_requisite(card, chat_id)}\n\n",
        f"{requisite_emoji('username')} <b>{tr(chat_id, 'Username для звезд', 'Username for Stars')}:</b>\n{shown_requisite(stars, chat_id)}\n\n",
        f"{requisite_emoji('send')} <b>{tr(chat_id, 'Отправьте реквизиты', 'Send requisites')}:</b>\n",
        tr(chat_id, "<i>Выберите, что хотите привязать.</i>", "<i>Choose what you want to bind.</i>"),
    ])
    keyboard = {
        "reply_markup": {
            "inline_keyboard": [
                [icon_button(tr(chat_id, "Привязать USDT", "Bind USDT"), "bind_usdt", callback_data="bind:usdt_ton_address", style="success")],
                [icon_button(tr(chat_id, "Привязать TON", "Bind TON"), "bind_ton", callback_data="bind:ton_address")],
                [icon_button(tr(chat_id, "Привязать Карту/СПБ", "Bind Card/SBP"), "bind_card_spb", callback_data="bind:card_spb_requisites", style="success")],
                [icon_button(tr(chat_id, "Привязать Username", "Bind Username"), "bind_username", callback_data="bind:stars_receiver")],
                [menu_button(chat_id=chat_id)],
            ]
        },
    }
    send_photo_or_text(chat_id, text, keyboard)

def send_bind_requisite(chat_id, session, key):
    session["step"] = "bind_requisite"
    session["binding_key"] = key

    texts = {
        "usdt_ton_address": tr(chat_id, "<b>Привязать USDT (TON)</b>\n\nОтправьте адрес для получения USDT в сети <b>TON</b>.\n\n", "<b>Bind USDT (TON)</b>\n\nSend the address for receiving USDT on the <b>TON</b> network.\n\n") + quote_block(tr(chat_id, "Пример", "Example"), "UQDx0...a9F3"),
        "ton_address": tr(chat_id, "<b>Привязать TON</b>\n\nОтправьте ваш TON-адрес для получения оплаты.\n\n", "<b>Bind TON</b>\n\nSend your TON address for receiving payments.\n\n") + quote_block(tr(chat_id, "Пример", "Example"), "UQC4...kP9x"),
        "card_spb_requisites": tr(chat_id, "<b>Привязать Карту/СПБ</b>\n\nОтправьте реквизиты одним сообщением.\n\n", "<b>Bind Card/SBP</b>\n\nSend the requisites in one message.\n\n") + quote_block(tr(chat_id, "Примеры", "Examples"), "SBP TBank - +7 912 345-67-89\nEuroBank - 5536 9141 2847 3956"),
        "stars_receiver": tr(chat_id, "<b>Привязать Username</b>\n\nОтправьте username для получения/вывода звезд.\n\n", "<b>Bind Username</b>\n\nSend the username for receiving/withdrawing Stars.\n\n") + quote_block(tr(chat_id, "Пример", "Example"), "@username"),
    }
    if key not in texts:
        session["step"] = "menu"
        send_requisites(chat_id)
        return
    send_text(chat_id, texts[key], {"parse_mode": "HTML", **back_keyboard("requisites", chat_id)})


def is_ton_address(value):
    cleaned = str(value or "").strip()
    if re.fullmatch(r"[UE]Q[A-Za-z0-9_-]{46,}", cleaned):
        return True
    if re.fullmatch(r"[A-Fa-f0-9]{48,64}", cleaned):
        return True
    if re.fullmatch(r"[A-Za-z0-9_-]{48,64}", cleaned) and any(char.isalpha() for char in cleaned) and any(char.isdigit() for char in cleaned):
        return True
    return False


def has_bank_name(value):
    return bool(re.search(r"[A-Za-zА-Яа-яЁё]{2,}", str(value or "")))


def has_card_or_phone(value):
    digits = normalize_id(value)
    return 10 <= len(digits) <= 19


def is_card_requisite(value):
    return has_bank_name(value) and has_card_or_phone(value)


def handle_requisite_input(message, session, text):
    chat_id = message["chat"]["id"]
    key = session.get("binding_key")
    if not key:
        session["step"] = "menu"
        send_requisites(chat_id)
        return
    if key == "stars_receiver" and not is_username(text):
        send_text(chat_id, tr(chat_id, "<b>Неверный username.</b>\n\nОтправьте username в формате:\n<code>@username</code>", "<b>Invalid username.</b>\n\nSend username in this format:\n<code>@username</code>"), {"parse_mode": "HTML", **back_keyboard("requisites", chat_id)})
        return
    if key in ("ton_address", "usdt_ton_address") and not is_ton_address(text):
        send_text(chat_id, tr(chat_id, "<b>Неправильный адрес.</b>\n\nОтправьте корректный TON-адрес, например:\n<code>UQDx0...a9F3</code>", "<b>Invalid address.</b>\n\nSend a valid TON address, for example:\n<code>UQDx0...a9F3</code>"), {"parse_mode": "HTML", **back_keyboard("requisites", chat_id)})
        return
    if key == "card_spb_requisites" and not is_card_requisite(text):
        send_text(chat_id, tr(chat_id, "<b>Неправильные реквизиты карты/СПБ.</b>\n\nУкажите банк и номер карты или телефона.\nПример:\n<code>TBank +7 912 345-67-89</code>", "<b>Invalid Card/SBP requisites.</b>\n\nEnter a bank and card number or phone number.\nExample:\n<code>TBank +7 912 345-67-89</code>"), {"parse_mode": "HTML", **back_keyboard("requisites", chat_id)})
        return
    set_user_requisite(chat_id, key, text)
    label = requisite_label(key)
    log_owner("".join([
        "🧾 Обновлены реквизиты\n",
        f"Пользователь: {format_user_short(user_snapshot(message.get('from', {})))}\n",
        f"Telegram ID: <code>{html.escape(str(chat_id))}</code>\n",
        f"Тип: <b>{html.escape(label)}</b>\n",
        f"Значение:\n<code>{html.escape(text)}</code>",
    ]))
    session["step"] = "menu"
    session.pop("binding_key", None)
    send_text(chat_id, quote_block("✅", tr(chat_id, f"{label} сохранены", f"{label} saved")) + f"\n<b>{html.escape(label)}:</b>\n<code>{html.escape(text)}</code>", {
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [{"text": tr(chat_id, "Реквизиты", "Requisites"), "callback_data": "requisites", "style": "primary"}],
                [menu_button(chat_id=chat_id)],
            ]
        },
    })


def send_security(chat_id):
    text = "".join([
        f"<b>🛡 {tr(chat_id, 'Безопасность', 'Security')}</b>\n\n",
        quote_block("•", tr(chat_id, f"Передавайте товар исключительно менеджеру {escrow_account()}", f"Transfer the item only to the manager {escrow_account()}")),
        quote_block("•", tr(chat_id, "Не отправляйте напрямую покупателю. Передача идёт через сервис", "Do not send directly to the buyer. The transfer goes through the service")),
        quote_block("•", tr(chat_id, "Сверяйте сумму и тег ордера в комментарии к платежу", "Check the amount and order tag in the payment comment")),
        quote_block("•", tr(chat_id, "После проверки покупатель подтверждает получение, и ордер закрывается", "After verification, the buyer confirms receipt and the order is closed")),
    ])
    send_photo_or_text(chat_id, text, back_keyboard("menu", chat_id))


def send_missing_requisites(chat_id, session):
    currency = session["order"].get("currency")
    display_name = display_currency(currency, session["order"].get("fiat"))
    title, body = requisite_missing_text(currency, display_name, chat_id)
    send_text(chat_id, f"<b>{html.escape(title)}</b>\n\n{html.escape(body)}\n\n{tr(chat_id, 'Привяжите реквизиты и повторите создание ордера.', 'Bind the requisites and create the order again.')}", {
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [{"text": tr(chat_id, "Реквизиты", "Requisites"), "callback_data": "requisites", "style": "primary"}],
                [back_button("product:" + session["order"].get("product", "nft_gift"), chat_id=chat_id)],
            ]
        },
    })


def send_owner_start(chat_id):
    send_text(chat_id, "".join([
        "<b>Привет, ты главный администратор этого сервиса.</b>\n\n",
        "Выбери задачу ниже.\n\n",
        admin_help_text(),
    ]), {
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "Управление админами", "callback_data": "admin_manage", "style": "primary"}],
                [{"text": "Меню пользователя", "callback_data": "user_menu", "style": "success"}],
            ]
        },
    })


def send_admin_manage(chat_id):
    admins = get_admins()
    users = load_json(STATS_FILE, {}).get("users", {})
    lines = ["<b>Админы сервиса:</b>\n"]
    keyboard = []
    if not admins:
        lines.append("Список пуст.")
    for admin_id in admins:
        admin_user = users.get(str(admin_id), {})
        shown = format_user_short(admin_user) if admin_user else f"ID {admin_id}"
        lines.append(f"• {html.escape(shown)} — <code>{html.escape(str(admin_id))}</code>")
        keyboard.append([{"text": f"Удалить {shown}", "callback_data": f"admin_remove:{admin_id}", "style": "danger"}])
    keyboard.append([back_button("owner_panel")])
    send_text(chat_id, "\n".join(lines), {"parse_mode": "HTML", "reply_markup": {"inline_keyboard": keyboard}})


def admin_help_text():
    return "".join([
        "<b>Команды админа:</b>\n",
        "<code>/buy тег_ордера</code> — оплатить ордер\n",
        "<code>/success ID количество</code> — накрутить успешные ордеры\n",
        "<code>/rating ID оценка</code> — добавить оценку рейтинга\n",
        "<code>/addbalance ID STARS 100</code> — пополнить баланс\n",
        "<code>/addadmin ID</code> — добавить админа, только главный админ",
    ])


def main_menu_keyboard():
    return {
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "Создать ордер", "callback_data": "create_order", "style": "success"}],
                [
                    {"text": "Пополнить/вывод", "callback_data": "deposit_withdraw", "style": "primary"},
                    {"text": "Реквизиты", "callback_data": "requisites", "style": "primary"},
                ],
                [
                    {"text": "Язык / Lang", "callback_data": "language", "style": "primary"},
                    {"text": "Профиль", "callback_data": "profile", "style": "primary"},
                ],
                [
                    {"text": "Рефералы", "callback_data": "referrals", "style": "primary"},
                    {"text": "Мои ордеры", "callback_data": "my_orders", "style": "primary"},
                ],
                [
                    {"text": "Тех.поддержка", "url": support_url(), "style": "danger"},
                    {"text": "Безопасность", "callback_data": "security", "style": "danger"},
                ],
            ]
        }
    }


def back_keyboard(callback_data, chat_id=None):
    return {
        "reply_markup": {
            "inline_keyboard": [[menu_button(callback_data, chat_id=chat_id)]]
        }
    }


def quote_block(label, text):
    label_text = f"<b>{html.escape(str(label))}</b> " if str(label) else ""
    return f"<blockquote>{label_text}{html.escape(str(text))}</blockquote>"


def send_photo_or_text(chat_id, text, keyboard):
    image_path = BASE_DIR / CONFIG.get("WELCOME_IMAGE_PATH", "assets/welcome.png")
    if image_path.exists():
        send_photo(chat_id, image_path, text, keyboard)
        return
    send_text(chat_id, text, {"parse_mode": "HTML", **keyboard})


def recipient_title(product):
    titles = {
        "nft_gift": "Получатель NFT-Gift",
        "nft_username": "Получатель NFT-username",
        "stars": "Получатель звезд",
        "ton": "Получатель TON",
        "telegram_premium": "Получатель Telegram Premium",
    }
    return titles.get(product, "Получатель")


def min_text(currency, fiat, chat_id=None):
    if currency == "STARS":
        return tr(chat_id, "Минимум: 100 звезд", "Minimum: 100 Stars")
    if currency == "TON":
        return tr(chat_id, "Минимум: 1 TON", "Minimum: 1 TON")
    if currency == "USDT_TON":
        return tr(chat_id, "Минимум: 1 USDT", "Minimum: 1 USDT")
    if currency == "CARD_SPB":
        return tr(chat_id, f"Минимум: {'10 RUB' if fiat == 'RUB' else '1 ' + (fiat or 'USD')}", f"Minimum: {'10 RUB' if fiat == 'RUB' else '1 ' + (fiat or 'USD')}")
    return tr(chat_id, "Минимум: 1", "Minimum: 1")


def display_currency(currency, fiat):
    if currency == "USDT_TON":
        return "USDT (TON)"
    if currency == "CARD_SPB":
        return fiat or "Карта/СПБ"
    if currency == "STARS":
        return "Stars"
    return currency or "STARS"


def balance_currency_key(order):
    if order.get("currency") == "CARD_SPB":
        return order.get("fiat") or "RUB"
    return order.get("currency") or "STARS"


def price_text(amount, currency):
    return f"{clean_amount(amount)} {currency}"


def clean_amount(amount):
    try:
        value = float(amount)
    except (TypeError, ValueError):
        return amount
    return int(value) if value.is_integer() else round(value, 2)


def has_requisites(chat_id, currency):
    requisites = get_user_requisites(chat_id)
    if currency == "TON":
        return bool(requisites.get("ton_address") or CONFIG.get("TON_ADDRESS"))
    if currency == "USDT_TON":
        return bool(requisites.get("usdt_ton_address") or CONFIG.get("USDT_TON_ADDRESS"))
    if currency == "STARS":
        return bool(requisites.get("stars_receiver") or CONFIG.get("STARS_RECEIVER"))
    if currency == "CARD_SPB":
        return bool(requisites.get("card_spb_requisites") or CONFIG.get("CARD_SPB_REQUISITES"))
    return True


def get_user_requisites(chat_id):
    return load_json(REQUISITES_FILE, {}).get(str(chat_id), {})


def set_user_requisite(chat_id, key, value):
    data = load_json(REQUISITES_FILE, {})
    user_data = data.setdefault(str(chat_id), {})
    user_data[key] = value
    save_json(REQUISITES_FILE, data)


def requisite_line(label, value):
    shown = value if value else "не указана"
    return f"<code>{html.escape(label)}:</code>\n{html.escape(shown)}\n\n"


def requisite_label(key):
    labels = {
        "usdt_ton_address": "USDT (TON)",
        "ton_address": "TON",
        "card_spb_requisites": "Карта/СПБ",
        "stars_receiver": "Username",
    }
    return labels.get(key, "Реквизиты")


def requisite_missing_text(currency, display_name, chat_id=None):
    if currency == "TON":
        return tr(chat_id, "У вас не привязан TON адрес", "TON address is not bound"), tr(chat_id, "Для ордера в TON нужно добавить адрес получения.", "For a TON order, add a receiving address.")
    if currency == "USDT_TON":
        return tr(chat_id, "У вас не привязан USDT (TON) адрес", "USDT (TON) address is not bound"), tr(chat_id, "Для ордера в USDT нужно добавить адрес получения в сети TON.", "For a USDT order, add a receiving address on the TON network.")
    if currency == "STARS":
        return tr(chat_id, "У вас не привязан получатель звезд", "Stars recipient is not bound"), tr(chat_id, "Для ордера в Stars нужно указать аккаунт получения.", "For a Stars order, specify the receiving account.")
    if currency == "CARD_SPB":
        return tr(chat_id, "У вас не привязаны реквизиты карты/СПБ", "Card/SBP requisites are not bound"), tr(chat_id, f"Для ордера в {display_name} нужно добавить реквизиты получения.", f"For an order in {display_name}, add receiving requisites.")
    return tr(chat_id, f"У вас не привязаны реквизиты {display_name}", f"{display_name} requisites are not bound"), tr(chat_id, "Добавьте реквизиты получения для выбранной валюты.", "Add receiving requisites for the selected currency.")


def get_balances(chat_id):
    return load_json(BALANCES_FILE, {}).get(str(chat_id), {})


def get_balance(chat_id, currency):
    return float_amount(str(get_balances(chat_id).get(currency, 0)), default=0)


def add_balance(chat_id, currency, amount):
    data = load_json(BALANCES_FILE, {})
    user_balances = data.setdefault(str(chat_id), {})
    user_balances[currency] = clean_amount(float_amount(str(user_balances.get(currency, 0)), default=0) + amount)
    save_json(BALANCES_FILE, data)


def save_balance_request(request_data):
    data = load_json(REQUESTS_FILE, {})
    data[request_data["id"]] = request_data
    save_json(REQUESTS_FILE, data)


def manager_requisites(currency):
    return CONFIG.get(f"{currency}_DEPOSIT_REQUISITES") or escrow_account()


def withdraw_requisites(chat_id, currency):
    requisites = get_user_requisites(chat_id)
    if currency == "TON":
        return requisites.get("ton_address", "")
    if currency == "USDT_TON":
        return requisites.get("usdt_ton_address", "")
    if currency == "STARS":
        return requisites.get("stars_receiver", "")
    if currency in ("RUB", "UAH", "USD", "BYN"):
        return requisites.get("card_spb_requisites", "")
    return ""


def has_withdraw_requisites(chat_id, currency):
    return bool(withdraw_requisites(chat_id, currency))


def withdraw_missing_text(currency, chat_id=None):
    if currency == "STARS":
        needed = tr(chat_id, "username для звезд", "Stars username")
    elif currency == "TON":
        needed = tr(chat_id, "TON-адрес", "TON address")
    elif currency == "USDT_TON":
        needed = tr(chat_id, "USDT (TON)-адрес", "USDT (TON) address")
    else:
        needed = tr(chat_id, "реквизиты карты/СПБ", "Card/SBP requisites")
    return "".join([
        tr(chat_id, "<b>Не указаны реквизиты для вывода.</b>\n\n", "<b>Withdrawal requisites are not specified.</b>\n\n"),
        tr(chat_id, f"Для вывода {currency_label(currency, currency)} нужно привязать {html.escape(needed)}.", f"To withdraw {currency_label(currency, currency)}, bind {html.escape(needed)}."),
    ])


def requisites_status(requisites, chat_id=None):
    return tr(chat_id, "заполнены", "filled") if any(requisites.values()) else tr(chat_id, "не указаны", "not specified")


def get_order(order_id):
    return load_json(ORDERS_FILE, {}).get(order_id)


def save_order(order):
    data = load_json(ORDERS_FILE, {})
    data[order["id"]] = order
    save_json(ORDERS_FILE, data)


def get_user_stats(user_id):
    stats = load_json(STATS_FILE, {})
    user_stats = stats.get(str(user_id), {})
    rating_count = int(user_stats.get("rating_count", 0))
    rating_sum = float(user_stats.get("rating_sum", 0))
    rating = rating_sum / rating_count if rating_count else 0
    return {
        "successful_orders": int(user_stats.get("successful_orders", 0)),
        "rating": rating,
        "rating_count": rating_count,
    }


def format_rating(stats):
    if stats.get("rating_count", 0) <= 0:
        return "0.0"
    return f"{stats['rating']:.1f}"


def increment_success(user):
    if not user or not user.get("id"):
        return
    change_success(user["id"], 1)


def change_success(user_id, delta):
    stats = load_json(STATS_FILE, {})
    user_stats = stats.setdefault(str(user_id), {"successful_orders": 0, "rating_sum": 0, "rating_count": 0})
    user_stats["successful_orders"] = max(0, int(user_stats.get("successful_orders", 0)) + delta)
    save_json(STATS_FILE, stats)


def add_rating(user_id, score):
    score = max(1, min(5, score))
    stats = load_json(STATS_FILE, {})
    user_stats = stats.setdefault(str(user_id), {"successful_orders": 0, "rating_sum": 0, "rating_count": 0})
    user_stats["rating_sum"] = float(user_stats.get("rating_sum", 0)) + score
    user_stats["rating_count"] = int(user_stats.get("rating_count", 0)) + 1
    save_json(STATS_FILE, stats)


def remember_user(user):
    if not user or not user.get("id"):
        return
    stats = load_json(STATS_FILE, {})
    users = stats.setdefault("users", {})
    users[str(user["id"])] = user_snapshot(user)
    save_json(STATS_FILE, stats)


def get_admins():
    data = load_json(ADMINS_FILE, {"admins": []})
    return [str(admin_id) for admin_id in data.get("admins", [])]


def add_admin(user_id):
    data = load_json(ADMINS_FILE, {"admins": []})
    admins = set(str(admin_id) for admin_id in data.get("admins", []))
    admins.add(str(user_id))
    data["admins"] = sorted(admins)
    save_json(ADMINS_FILE, data)


def remove_admin(user_id):
    data = load_json(ADMINS_FILE, {"admins": []})
    data["admins"] = [str(admin_id) for admin_id in data.get("admins", []) if str(admin_id) != str(user_id)]
    save_json(ADMINS_FILE, data)


def is_owner(user_id):
    return str(user_id) == str(CONFIG.get("OWNER_ID", ""))


def is_admin(user_id):
    return str(user_id) in get_admins()


def is_admin_or_owner(user_id):
    return is_owner(user_id) or is_admin(user_id)


def log_owner(text):
    owner_ids = admin_ids_from_config("OWNER_ID", "OWNER_IDS", "MAIN_ADMIN_ID", "MAIN_ADMIN_IDS")
    for owner_id in owner_ids:
        try:
            send_text(owner_id, text, {"parse_mode": "HTML"})
        except RuntimeError as error:
            print(f"Owner log failed for {owner_id}: {error}")


def register_referral(user, code):
    owner_id = decode_referral_code(code)
    if not owner_id or str(owner_id) == str(user.get("id")):
        return
    data = load_json(REFERRALS_FILE, {"invited": {}, "by_user": {}})
    user_id = str(user.get("id"))
    if data["by_user"].get(user_id):
        return
    data["by_user"][user_id] = str(owner_id)
    data["invited"].setdefault(str(owner_id), []).append(user_id)
    save_json(REFERRALS_FILE, data)


def referral_code(user_id):
    return "z" + base36(int(user_id or 0))


def decode_referral_code(code):
    if not code.startswith("z"):
        return None
    try:
        return int(code[1:], 36)
    except ValueError:
        return None


def base36(number):
    alphabet = string.digits + string.ascii_lowercase
    if number == 0:
        return "0"
    result = ""
    while number:
        number, index = divmod(number, 36)
        result = alphabet[index] + result
    return result


def collect_emoji(message):
    entities = list(message.get("entities", [])) + list(message.get("caption_entities", []))
    custom = [entity for entity in entities if entity.get("type") == "custom_emoji"]
    if not custom:
        send_text(message["chat"]["id"], "В этом сообщении нет Telegram custom emoji. Отправь именно премиум-эмодзи.")
        return

    ids = [str(entity.get("custom_emoji_id")) for entity in custom if entity.get("custom_emoji_id")]
    stickers = {}
    try:
        response = api("getCustomEmojiStickers", {"custom_emoji_ids": ids})
        stickers = {item.get("custom_emoji_id"): item for item in response.get("result", [])}
    except Exception:
        stickers = {}

    lines = []
    for index, emoji_id in enumerate(ids, start=1):
        sticker = stickers.get(emoji_id, {})
        base_emoji = sticker.get("emoji") or "emoji"
        set_name = sticker.get("set_name") or "unknown_set"
        lines.append(f"{index}. {base_emoji} custom_emoji_id={emoji_id} / {set_name}")

    send_text(message["chat"]["id"], "Нашел premium/custom emoji:\n" + "\n".join(lines) + "\n\nВставь нужные ID в settings.py.")

def emoji_diagnostic_text():
    keys = [
        "EMOJI_WELCOME", "EMOJI_SERVICE", "EMOJI_SPEED", "EMOJI_AUTO",
        "EMOJI_STEP_1", "EMOJI_STEP_2", "EMOJI_STEP_3", "EMOJI_STEP_4", "EMOJI_DOWN",
    ]
    ids = [clean_emoji_id(CONFIG.get(key, "")) for key in keys]
    stickers = {}
    if any(ids):
        try:
            response = api("getCustomEmojiStickers", {"custom_emoji_ids": [emoji_id for emoji_id in ids if emoji_id]})
            stickers = {item.get("custom_emoji_id"): item for item in response.get("result", [])}
        except Exception as error:
            return "<b>Ошибка проверки emoji:</b>\n<code>" + html.escape(str(error)) + "</code>"

    lines = ["<b>Проверка premium/custom emoji</b>", ""]
    for key, emoji_id in zip(keys, ids):
        if not emoji_id:
            lines.append(f"<code>{key}</code>: пусто")
            continue
        sticker = stickers.get(emoji_id)
        if not sticker:
            lines.append(f"<code>{key}</code>: ID не найден Telegram")
            continue
        base_emoji = sticker.get("emoji", "")
        set_name = sticker.get("set_name", "")
        lines.append(f"<code>{key}</code>: {html.escape(base_emoji)} <code>{html.escape(emoji_id)}</code> / <code>{html.escape(set_name)}</code>")

    lines.extend([
        "",
        "Если здесь показаны не те иконки, значит в настройках стоят ID не от нужных premium emoji.",
        "Отправь боту команду <code>/emoji</code>, затем отправь нужные premium emoji из Telegram, и замени ID в <code>settings.py</code>.",
    ])
    return "\n".join(lines)


def api(method, payload):
    token = CONFIG["BOT_TOKEN"]
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} HTTP {error.code}: {body}") from error
    if not result.get("ok"):
        raise RuntimeError(f"{method} failed: {result}")
    return result


def safe_html_text(text):
    text = re.sub(r'<tg-emoji\s+emoji-id="[^"]+">(.*?)</tg-emoji>', r'\1', str(text), flags=re.DOTALL)
    text = text.replace("<blockquote>", "").replace("</blockquote>", "")
    return text


def should_retry_plain_html(error):
    return "ENTITY_TEXT_INVALID" in str(error) or "DOCUMENT_INVALID" in str(error) or "can't parse entities" in str(error).lower()


def send_text(chat_id, text, extra=None):
    payload = {"chat_id": chat_id, "text": text}
    if extra:
        payload.update(extra)
    try:
        return api("sendMessage", payload)
    except RuntimeError as error:
        if not should_retry_plain_html(error):
            raise
        retry_payload = dict(payload)
        retry_payload["text"] = safe_html_text(text)
        return api("sendMessage", retry_payload)


def send_photo_only(chat_id, file_path):
    token = CONFIG["BOT_TOKEN"]
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    fields = {"chat_id": str(chat_id)}
    response = multipart_post(url, fields, "photo", file_path)
    if not response.get("ok"):
        raise RuntimeError(f"sendPhoto failed: {response}")
    return response


def send_photo(chat_id, file_path, caption, extra=None):
    token = CONFIG["BOT_TOKEN"]
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    fields = {"chat_id": str(chat_id), "caption": caption, "parse_mode": "HTML"}
    if extra:
        for key, value in extra.items():
            fields[key] = json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else str(value)
    try:
        response = multipart_post(url, fields, "photo", file_path)
    except RuntimeError as error:
        if not should_retry_plain_html(error):
            raise
        send_photo_only(chat_id, file_path)
        return send_text(chat_id, caption, {"parse_mode": "HTML", **(extra or {})})
    if not response.get("ok"):
        raise RuntimeError(f"sendPhoto failed: {response}")
    return response


def multipart_post(url, fields, file_field, file_path):
    boundary = "----EscrowVaultBoundary" + "".join(random.choice(string.ascii_letters) for _ in range(12))
    body = bytearray()
    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        body.extend(str(value).encode("utf-8"))
        body.extend(b"\r\n")
    mime_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="{file_field}"; filename="{file_path.name}"\r\n'.encode("utf-8"))
    body.extend(f"Content-Type: {mime_type}\r\n\r\n".encode("utf-8"))
    body.extend(file_path.read_bytes())
    body.extend(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    request = urllib.request.Request(url, data=bytes(body), headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"multipart HTTP {error.code}: {body}") from error


def load_env(file_path):
    values = {}
    if settings:
        for key in dir(settings):
            if key.isupper():
                values[key] = str(getattr(settings, key))
    if file_path.exists():
        for raw_line in file_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values.setdefault(key.strip(), value.strip())
    for key, value in os.environ.items():
        values[key] = value
    return values


def load_json(file_path, fallback):
    if not file_path.exists():
        return fallback
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fallback


def save_json(file_path, data):
    DATA_DIR.mkdir(exist_ok=True)
    file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_session(chat_id):
    if chat_id not in SESSIONS:
        saved_lang = get_user_language(chat_id)
        SESSIONS[chat_id] = {"lang": saved_lang, "step": "menu" if saved_lang else "language", "order": {}}
    return SESSIONS[chat_id]


def is_duplicate_callback(chat_id, user_id, data):
    now = time.time()
    stale_keys = [key for key, timestamp in CALLBACK_DEDUP.items() if now - timestamp > 30]
    for key in stale_keys:
        CALLBACK_DEDUP.pop(key, None)

    key = (str(chat_id), str(user_id or ""), str(data or ""))
    previous = CALLBACK_DEDUP.get(key)
    CALLBACK_DEDUP[key] = now
    return previous is not None and now - previous < CALLBACK_DEDUP_SECONDS


def is_username(value):
    if not value.startswith("@"):
        return False
    name = value[1:]
    return 5 <= len(name) <= 32 and all(char.isalnum() or char == "_" for char in name)


def user_snapshot(user):
    return {
        "id": user.get("id"),
        "username": user.get("username"),
        "first_name": user.get("first_name"),
        "chat_id": user.get("id"),
    }


def username(user):
    if user.get("username"):
        return "@" + user["username"]
    return user.get("first_name") or "user"


def format_user_short(user):
    if not user:
        return "не подключен"
    return username(user)


def user_chat_id(user):
    if not user:
        return None
    return user.get("chat_id") or user.get("id")


def float_amount(value, default=0):
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default


def int_amount(value, default=0):
    try:
        return int(float_amount(value, default=default))
    except (TypeError, ValueError):
        return default


def make_order_id():
    return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(10))


def make_request_id():
    return "rq" + "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(8))


def escrow_account():
    return CONFIG.get("ESCROW_ACCOUNT") or "@EscrowManager"


def manager_url():
    return "https://t.me/" + escrow_account().lstrip("@")


def support_url():
    return "https://t.me/" + (CONFIG.get("SUPPORT_USERNAME") or escrow_account()).lstrip("@")


def normalize_id(value):
    return "".join(char for char in str(value or "") if char.isdigit())


def admin_ids_from_config(*keys):
    ids = set()
    for key in keys:
        raw = str(CONFIG.get(key, "") or "")
        for part in raw.replace(";", ",").replace(" ", ",").split(","):
            cleaned = normalize_id(part)
            if cleaned:
                ids.add(cleaned)
    return ids


def is_owner(user_id):
    return normalize_id(user_id) in admin_ids_from_config("OWNER_ID", "OWNER_IDS", "MAIN_ADMIN_ID", "MAIN_ADMIN_IDS")


def is_admin(user_id):
    normalized = normalize_id(user_id)
    return normalized in {normalize_id(admin_id) for admin_id in get_admins()} or normalized in admin_ids_from_config("ADMIN_ID", "ADMIN_IDS")


def is_admin_or_owner(user_id):
    return is_owner(user_id) or is_admin(user_id)


def send_owner_start(chat_id):
    send_text(chat_id, "".join([
        "<b>Привет, ты главный администратор этого сервиса.</b>\n\n",
        "Выбери задачу ниже.",
    ]), {
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "Управление админами", "callback_data": "admin_manage", "style": "primary"}],
                [{"text": "Админ-панель", "callback_data": "admin_panel", "style": "success"}],
                [{"text": "Все команды", "callback_data": "admin_commands", "style": "primary"}],
                [{"text": "Меню пользователя", "callback_data": "user_menu", "style": "primary"}],
            ]
        },
    })


def send_admin_panel(chat_id):
    send_text(chat_id, "".join([
        "<b>Админ-панель</b>\n\n",
        "Выберите действие ниже. Обычный админ может оплатить ордер, пополнить баланс пользователю, накрутить успешные ордеры и рейтинг.",
    ]), {
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "Команды оплаты", "callback_data": "admin_commands", "style": "success"}],
                [{"text": "Пополнение баланса", "callback_data": "admin_balance_help", "style": "primary"}],
                [{"text": "Меню пользователя", "callback_data": "user_menu", "style": "primary"}],
            ]
        },
    })


def send_admin_commands(chat_id, owner=False):
    send_text(chat_id, admin_help_text(owner), {
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "Пополнение баланса", "callback_data": "admin_balance_help", "style": "success"}],
                [back_button("owner_panel" if owner else "admin_panel")],
            ]
        },
    })


def send_admin_balance_help(chat_id):
    send_text(chat_id, "".join([
        "<b>Пополнение баланса пользователю</b>\n\n",
        "Используй команду:\n",
        "<code>/addbalance ID STARS 100</code>\n\n",
        "Валюты: <code>STARS</code>, <code>TON</code>, <code>USDT_TON</code>, <code>RUB</code>, <code>UAH</code>, <code>USD</code>, <code>BYN</code>.\n\n",
        "Пример:\n",
        "<code>/addbalance 5246733007 STARS 100</code>",
    ]), {
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [[back_button("admin_panel")]]
        },
    })


def send_access_denied(chat_id):
    send_text(chat_id, "<b>Доступ запрещён.</b>\n\nЭта команда доступна только администраторам сервиса.", {
        "parse_mode": "HTML",
    })


def admin_help_text(owner=False):
    lines = [
        "<b>Команды админа:</b>",
        "<code>/admin</code> — открыть админ-панель",
        "<code>/buy тег_ордера</code> — оплатить ордер",
        "<code>/success ID количество</code> — накрутить успешные ордеры",
        "<code>/rating ID оценка</code> — добавить оценку рейтинга",
        "<code>/addbalance ID STARS 100</code> — пополнить баланс",
    ]
    if owner:
        lines.append("<code>/addadmin ID</code> — добавить админа")
    return "\n".join(lines)


def send_owner_start(chat_id):
    send_text(chat_id, "".join([
        "<b>Привет, ты главный администратор этого сервиса.</b>\n\n",
        "Выбери задачу ниже.",
    ]), {
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "Управление админами", "callback_data": "admin_manage", "style": "primary"}],
                [{"text": "Админ-панель", "callback_data": "admin_panel", "style": "success"}],
                [{"text": "Все команды", "callback_data": "admin_commands", "style": "success"}],
                [{"text": "Меню пользователя", "callback_data": "user_menu", "style": "primary"}],
            ]
        },
    })


def send_admin_panel(chat_id):
    send_text(chat_id, "<b>Vault Admin</b>\n\nВыберите действие ниже.", {
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "Все команды", "callback_data": "admin_commands", "style": "success"}],
                [{"text": "Меню пользователя", "callback_data": "user_menu", "style": "primary"}],
            ]
        },
    })


def send_admin_commands(chat_id, owner=False):
    send_text(chat_id, admin_help_text(owner), {
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [back_button("owner_panel" if owner else "admin_panel")],
            ]
        },
    })


def admin_help_text(owner=False):
    lines = [
        "<b>Команды админа:</b>",
        "<code>/vault admin</code> — открыть админ-панель",
        "<code>/buy тег_ордера</code> — оплатить ордер",
        "<code>/success ID количество</code> — накрутить успешные ордеры",
        "<code>/rating ID оценка</code> — добавить оценку рейтинга",
        "<code>/addbalance ID STARS 100</code> — пополнить баланс",
    ]
    if owner:
        lines.append("<code>/addadmin ID</code> — добавить админа")
        lines.append("<code>/deladmin ID</code> — удалить админа")
    return "\n".join(lines)


def send_menu_with_premium_text(chat_id, text, keyboard):
    image_path = BASE_DIR / CONFIG.get("WELCOME_IMAGE_PATH", "assets/welcome.png")
    if image_path.exists():
        send_photo_only(chat_id, image_path)
    send_text(chat_id, text, {"parse_mode": "HTML", **keyboard})


def send_welcome(chat_id, session):
    send_menu_with_premium_text(chat_id, welcome_text(chat_id), main_menu_keyboard(chat_id))


def send_main_menu(chat_id, session):
    send_menu_with_premium_text(chat_id, welcome_text(chat_id), main_menu_keyboard(chat_id))


def welcome_text(chat_id=None):
    blocks = [
        quote_block("1", tr(chat_id, "Автоматические сделки с NFT и подарками.", "Automated deals with NFTs and gifts.")),
        quote_block("2", tr(chat_id, "Полная защита обеих сторон.", "Full protection for both sides.")),
        quote_block("3", tr(chat_id, "Средства заморожены до подтверждения.", "Funds are locked until confirmation.")),
        quote_block("4", tr(chat_id, f"Передача через менеджера: {escrow_account()}", f"Transfer through the manager: {escrow_account()}")),
    ]
    return "".join([
        "<b>EscrowVault</b>\n\n",
        "\n".join(blocks),
        "\n\n",
        f"<b>{tr(chat_id, 'Выберите действие ниже', 'Choose an action below')}</b>",
    ])


def main_menu_keyboard(chat_id=None):
    icons = {
        "create_order": "5303400229549135579",
        "deposit_withdraw": "5402104393396931859",
        "language": "5454102570312166471",
        "support": "5454068128969417666",
        "referrals": "5197252827247841976",
        "requisites": "5454134258580877567",
        "profile": "5454134554933619492",
        "my_orders": "5454209184285356042",
        "security": "5260249805522744465",
    }

    def button(text, icon_key, callback_data=None, url=None, style="primary"):
        item = {
            "text": text,
            "icon_custom_emoji_id": icons[icon_key],
            "style": style,
        }
        if callback_data:
            item["callback_data"] = callback_data
        if url:
            item["url"] = url
        return item

    return {
        "reply_markup": {
            "inline_keyboard": [
                [button(tr(chat_id, "Создать ордер", "Create order"), "create_order", callback_data="create_order", style="success")],
                [
                    button(tr(chat_id, "Баланс", "Balance"), "deposit_withdraw", callback_data="deposit_withdraw"),
                    button(tr(chat_id, "Реквизиты", "Requisites"), "requisites", callback_data="requisites"),
                ],
                [
                    button(tr(chat_id, "Язык", "Language"), "language", callback_data="language"),
                    button(tr(chat_id, "Профиль", "Profile"), "profile", callback_data="profile"),
                ],
                [
                    button(tr(chat_id, "Рефералы", "Referrals"), "referrals", callback_data="referrals"),
                    button(tr(chat_id, "Мои ордеры", "My orders"), "my_orders", callback_data="my_orders"),
                ],
                [
                    button(tr(chat_id, "Поддержка", "Support"), "support", url=support_url(), style="danger"),
                    button(tr(chat_id, "Безопасность", "Security"), "security", callback_data="security", style="danger"),
                ],
            ]
        }
    }

CUSTOM_EMOJI_ALTS = {
    "EMOJI_WELCOME": "❕",
    "EMOJI_SERVICE": "🐶",
    "EMOJI_SPEED": "🚀",
    "EMOJI_AUTO": "📱",
    "EMOJI_STEP_1": "1️⃣",
    "EMOJI_STEP_2": "2️⃣",
    "EMOJI_STEP_3": "3️⃣",
    "EMOJI_STEP_4": "4️⃣",
    "EMOJI_DOWN": "🔛",
}


def clean_emoji_id(value):
    return str(value or "").strip().strip('"').strip("'")


def premium_emoji(config_key, fallback):
    emoji_id = clean_emoji_id(CONFIG.get(config_key, ""))
    alt = CONFIG.get(f"{config_key}_ALT") or CUSTOM_EMOJI_ALTS.get(config_key, fallback)
    if not emoji_id:
        return html.escape(alt)
    return f'<tg-emoji emoji-id="{html.escape(emoji_id)}">{html.escape(alt)}</tg-emoji>'


def premium_quote(config_key, fallback, text):
    return f"<blockquote>{premium_emoji(config_key, fallback)} {html.escape(str(text))}</blockquote>"


def welcome_text(chat_id=None):
    if lang_for(chat_id) == "en":
        return "".join([
            f"{premium_emoji('EMOJI_WELCOME', '👋')} <b>Welcome!</b>\n\n",
            "<blockquote>",
            f"{premium_emoji('EMOJI_SERVICE', '🏠')} EscrowVault is a specialized service for\n",
            "secure OTC deals.\n",
            f"{premium_emoji('EMOJI_AUTO', '🛡')} Automated execution flow. Convenient and\n",
            "fast withdrawals",
            "</blockquote>",
            "\n\n",
            premium_quote("EMOJI_STEP_1", "1", "Automated deals with NFTs and gifts."),
            "\n",
            premium_quote("EMOJI_STEP_2", "2", "Full protection for both sides."),
            "\n",
            premium_quote("EMOJI_STEP_3", "3", "Funds are locked until confirmation."),
            "\n",
            premium_quote("EMOJI_STEP_4", "4", f"Transfer through the manager: {escrow_account()}"),
            "\n\n",
            "<blockquote>",
            f"<b>Choose an action below</b> {premium_emoji('EMOJI_DOWN', '⬇️')}",
            "</blockquote>",
        ])
    return "".join([
        f"{premium_emoji('EMOJI_WELCOME', '👋')} <b>Добро пожаловать!</b>\n\n",
        "<blockquote>",
        f"{premium_emoji('EMOJI_SERVICE', '🏠')} EscrowVault — специализированный сервис по\n",
        "обеспечению безопасности внебиржевых сделок.\n",
        f"{premium_emoji('EMOJI_AUTO', '🛡')} Автоматизированный алгоритм исполнения. Удобный и\n",
        "быстрый вывод средств",
        "</blockquote>",
        "\n\n",
        premium_quote("EMOJI_STEP_1", "1", "Автоматические сделки с NFT и подарками."),
        "\n",
        premium_quote("EMOJI_STEP_2", "2", "Полная защита обеих сторон."),
        "\n",
        premium_quote("EMOJI_STEP_3", "3", "Средства заморожены до подтверждения."),
        "\n",
        premium_quote("EMOJI_STEP_4", "4", f"Передача через менеджера: {escrow_account()}"),
        "\n\n",
        "<blockquote>",
        f"<b>Выберите действие ниже</b> {premium_emoji('EMOJI_DOWN', '⬇️')}",
        "</blockquote>",
    ])

def get_user_language(chat_id):
    return load_json(USER_SETTINGS_FILE, {}).get(str(chat_id), {}).get("lang")


def set_user_language(chat_id, lang):
    data = load_json(USER_SETTINGS_FILE, {})
    user_data = data.setdefault(str(chat_id), {})
    user_data["lang"] = lang
    save_json(USER_SETTINGS_FILE, data)


def send_profile(chat_id, user):
    stats = get_user_stats(user.get("id"))
    requisites = get_user_requisites(chat_id)
    text = "\n".join([
        f"{order_emoji('profile_title')} <b>{tr(chat_id, 'Профиль', 'Profile')}</b>",
        "",
        f"{order_emoji('profile_username')} <b>Username:</b> {html.escape(username(user))}",
        "",
        f"{order_emoji('profile_id')} <b>ID:</b> {html.escape(str(user.get('id')))}",
        "",
        f"{order_emoji('profile_rating')} <b>{tr(chat_id, 'Рейтинг', 'Rating')}:</b> {html.escape(format_rating(stats))}",
        "",
        f"{order_emoji('profile_success')} <b>{tr(chat_id, 'Успешных ордеров', 'Successful orders')}:</b> {stats['successful_orders']}",
        "",
        f"{order_emoji('profile_requisites')} <b>{tr(chat_id, 'Реквизиты', 'Requisites')}:</b> {html.escape(requisites_status(requisites, chat_id))}",
    ])
    send_text(chat_id, text, {
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [icon_button(tr(chat_id, "Проверить баланс", "Check balance"), "check_balance", callback_data="check_balance", style="success")],
                [menu_button(chat_id=chat_id)],
            ]
        },
    })

def send_security(chat_id):
    rule_2 = tr(chat_id, "Не отправляйте товар напрямую покупателю.\nПередача идёт через сервис.", "Do not send the item directly to the buyer.\nThe transfer goes through the service.")
    rule_3 = tr(chat_id, "Сверяйте сумму и тег ордера\nв комментарии к платежу.", "Check the amount and order tag\nin the payment comment.")
    rule_4 = tr(chat_id, "После проверки покупатель подтверждает\nполучение, и ордер закрывается.", "After verification, the buyer confirms\nreceipt and the order is closed.")
    text = "\n".join([
        f"{order_emoji('security_title')} <b>{tr(chat_id, 'Безопасность', 'Security')}</b>",
        "",
        f"{order_emoji('order_1')} {tr(chat_id, 'Передавайте товар только менеджеру', 'Transfer the item only to the manager')}:\n{html.escape(escrow_account())}",
        "",
        f"{order_emoji('order_2')} {rule_2}",
        "",
        f"{order_emoji('order_3')} {rule_3}",
        "",
        f"{order_emoji('order_4')} {rule_4}",
    ])
    send_photo_or_text(chat_id, text, back_keyboard("menu", chat_id))

def utf16_len(text):
    return len(text.encode("utf-16-le")) // 2


def send_start_menu(chat_id):
    text = welcome_text(chat_id)
    keyboard = main_menu_keyboard(chat_id)
    image_path = BASE_DIR / CONFIG.get("WELCOME_IMAGE_PATH", "assets/welcome.png")

    if image_path.exists():
        return send_photo(chat_id, image_path, text, keyboard)

    return send_text(chat_id, text, {
        "parse_mode": "HTML",
        **keyboard,
    })

def send_welcome(chat_id, session):
    return send_start_menu(chat_id)


def send_main_menu(chat_id, session):
    return send_start_menu(chat_id)


if __name__ == "__main__":
    main()




































