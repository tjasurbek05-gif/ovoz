import logging
import json
import asyncio
import nest_asyncio
import os
import time
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
import edge_tts

# Apply fix for loops
nest_asyncio.apply()

# --- CONFIGURATION ---
TOKEN = '8427271861:AAGGo6CFHUWdSanzwc4VPDXDynUDrVBkUXs'  # <--- PASTE YOUR TOKEN HERE

# Store user settings in memory (Dictionary)
user_settings = {}

DEFAULT_SETTINGS = {
    'voice': 'uz-UZ-MadinaNeural',
    'rate': '+0%',
    'pitch': '+0Hz'
}

# Preset speeds offered in the bot chat (label, rate percentage)
SPEED_OPTIONS = [
    ("🐢 Sekin", -25),
    ("🚶 Birmuncha sekin", -10),
    ("▶️ Normal", 0),
    ("🏃 Tez", 25),
    ("🚀 Juda tez", 50),
]


def current_rate_value(user_id):
    """Returns the user's current speed as an int percentage (e.g. 0, 25, -25)."""
    rate = user_settings.get(user_id, DEFAULT_SETTINGS).get('rate', '+0%')
    return int(str(rate).replace('%', ''))


def build_speed_keyboard(current_rate):
    rows = []
    for label, value in SPEED_OPTIONS:
        text = f"✅ {label} ({value:+d}%)" if value == current_rate else f"{label} ({value:+d}%)"
        rows.append([InlineKeyboardButton(text, callback_data=f"speed_{value}")])
    return InlineKeyboardMarkup(rows)


# ... previous imports ...

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends the welcome message with the Mini App button."""

    # PASTE YOUR GITHUB URL HERE 👇
    web_app_url = "https://jtojiboyev253-alt.github.io/uzbektts/"

    keyboard = [
        [KeyboardButton(
            text="⚙️ Ovozni Sozlash (Settings)",
            web_app=WebAppInfo(url=web_app_url)
        )],
        [KeyboardButton(text="⚡ Tezlikni sozlash")]
    ]
    # ... rest of the code is the same ...
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "Assalomu alaykum! Men o'zbek tili TTS botiman.\n"
        "Iltimos, pastdagi tugmani bosib ovoz sozlamalarini tanlang, "
        "yoki \"⚡ Tezlikni sozlash\" tugmasi (yoki /tezlik) orqali gapirish tezligini o'zgartiring!",
        reply_markup=reply_markup
    )


async def speed_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows an inline keyboard to pick the speech speed, right in the chat."""
    user_id = update.effective_user.id
    await update.message.reply_text(
        "⚡ Ovoz tezligini tanlang:",
        reply_markup=build_speed_keyboard(current_rate_value(user_id))
    )


async def speed_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles a speed button press and saves it without touching other settings."""
    query = update.callback_query
    user_id = query.from_user.id
    value = int(query.data.split('_', 1)[1])
    previous_value = current_rate_value(user_id)

    settings = user_settings.get(user_id, dict(DEFAULT_SETTINGS))
    settings['rate'] = f"{value:+d}%"
    user_settings[user_id] = settings

    await query.answer(f"Tezlik {value:+d}% ga o'rnatildi ✅")
    if value != previous_value:
        # Skip the edit when re-tapping the already-selected speed: Telegram
        # rejects edit_message_reply_markup calls with unchanged markup.
        await query.edit_message_reply_markup(reply_markup=build_speed_keyboard(value))


async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the data coming back from the Mini App."""
    user_id = update.effective_user.id
    data = json.loads(update.effective_message.web_app_data.data)

    # Merge into existing settings so a speed picked via /tezlik isn't wiped out
    settings = user_settings.get(user_id, dict(DEFAULT_SETTINGS))
    settings.update(data)
    user_settings[user_id] = settings

    await update.message.reply_text(
        f"✅ Sozlamalar saqlandi!\n\n"
        f"🎙 Ovoz: {settings['voice']}\n"
        f"🎚 Balandlik: {settings['pitch']}\n\n"
        f"⚡ Tezlikni sozlash uchun \"⚡ Tezlikni sozlash\" tugmasi yoki /tezlik buyrug'idan foydalaning.\n\n"
        "Endi menga istalgan matnni yuboring, men uni ovozga aylantirib beraman."
    )


# ... (keep your other imports) ...

async def generate_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receives text and sends back audio. Safer version."""
    user_id = update.effective_user.id
    text = update.message.text
    
    if not text:
        return

    # Print to terminal so you can see if your friend's message arrives
    print(f"📩 Message from {update.effective_user.first_name}: {text}")

    await update.message.reply_chat_action("record_voice")

    # 1. Get settings (Safe Default if they never used the app)
    settings = user_settings.get(user_id, DEFAULT_SETTINGS)

    # 2. Create a UNIQUE filename (using time) so files never conflict
    timestamp = int(time.time())
    output_file = f"voice_{user_id}_{timestamp}.mp3"

    try:
        # 3. Generate Audio
        communicate = edge_tts.Communicate(
            text,
            settings.get('voice', DEFAULT_SETTINGS['voice']),
            rate=settings.get('rate', DEFAULT_SETTINGS['rate']),
            pitch=settings.get('pitch', DEFAULT_SETTINGS['pitch'])
        )
        await communicate.save(output_file)
        
        # 4. Send Audio
        # We use 'open' inside a 'with' block to ensure it closes
        with open(output_file, 'rb') as audio:
             await update.message.reply_audio(
                 audio=audio, 
                 title=f"Audio for {update.effective_user.first_name}",
                 performer="Uzbek AI"
             )
        
        print(f"✅ Audio sent to {update.effective_user.first_name}")

    except Exception as e:
        print(f"❌ ERROR sending to {update.effective_user.first_name}: {e}")
        await update.message.reply_text("Kechirasiz, ovoz yaratishda xatolik bo'ldi.")
        
    finally:
        # 5. CLEANUP: Delete the file from your laptop
        if os.path.exists(output_file):
            try:
                os.remove(output_file)
            except:
                pass # If we can't delete it, just ignore it

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('tezlik', speed_command))
    # Handle speed button presses (inline keyboard)
    app.add_handler(CallbackQueryHandler(speed_callback, pattern=r"^speed_-?\d+$"))
    # Handle data from Web App
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))
    # Handle the "⚡ Tezlikni sozlash" reply-keyboard button (must be before the generic text handler)
    app.add_handler(MessageHandler(filters.Regex("^⚡ Tezlikni sozlash$"), speed_command))
    # Handle text messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_audio))

    print("Bot ishga tushdi...")
    app.run_polling()