import logging
import json
import asyncio
import nest_asyncio
import os
import time
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import edge_tts

# Apply fix for loops
nest_asyncio.apply()

# --- CONFIGURATION ---
TOKEN = '8427271861:AAGGo6CFHUWdSanzwc4VPDXDynUDrVBkUXs'  # <--- PASTE YOUR TOKEN HERE

# Store user settings in memory (Dictionary)
user_settings = {}

# ... previous imports ...

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends the welcome message with the Mini App button."""
    
    # PASTE YOUR GITHUB URL HERE 👇
    web_app_url = "https://jtojiboyev253-alt.github.io/uzbektts/" 
    
    keyboard = [
        [KeyboardButton(
            text="⚙️ Ovozni Sozlash (Settings)", 
            web_app=WebAppInfo(url=web_app_url)
        )]
    ]
    # ... rest of the code is the same ...
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "Assalomu alaykum! Men o'zbek tili TTS botiman.\n"
        "Iltimos, pastdagi tugmani bosib ovoz sozlamalarini tanlang!",
        reply_markup=reply_markup
    )

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the data coming back from the Mini App."""
    user_id = update.effective_user.id
    data = json.loads(update.effective_message.web_app_data.data)
    
    # Save settings for this user
    user_settings[user_id] = data
    
    await update.message.reply_text(
        f"✅ Sozlamalar saqlandi!\n\n"
        f"🎙 Ovoz: {data['voice']}\n"
        f"⚡ Tezlik: {data['rate']}\n"
        f"🎚 Balandlik: {data['pitch']}\n\n"
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
    defaults = {
        'voice': 'uz-UZ-MadinaNeural',
        'rate': '+0%',
        'pitch': '+0Hz'
    }
    settings = user_settings.get(user_id, defaults)

    # 2. Create a UNIQUE filename (using time) so files never conflict
    timestamp = int(time.time())
    output_file = f"voice_{user_id}_{timestamp}.mp3"
    
    try:
        # 3. Generate Audio
        communicate = edge_tts.Communicate(
            text, 
            settings.get('voice', defaults['voice']), 
            rate=settings.get('rate', defaults['rate']), 
            pitch=settings.get('pitch', defaults['pitch'])
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
    # Handle data from Web App
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))
    # Handle text messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_audio))

    print("Bot ishga tushdi...")
    app.run_polling()