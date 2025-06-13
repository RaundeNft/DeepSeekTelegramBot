import os
import json
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)

# Load secrets from .env
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Load or initialize chat memory
HISTORY_FILE = "chat_history.json"
if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "r") as f:
        chat_memory = json.load(f)
else:
    chat_memory = {}

def save_chat():
    with open(HISTORY_FILE, "w") as f:
        json.dump(chat_memory, f, indent=2)

# 🧠 Handle text messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    user_msg = update.message.text

    if user_id not in chat_memory:
        chat_memory[user_id] = []

    chat_memory[user_id].append({"role": "user", "content": user_msg})

    response = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "deepseek-chat",  # or deepseek-coder
            "messages": chat_memory[user_id],
            "stream": False
        }
    )

    if response.status_code == 200:
        reply = response.json()['choices'][0]['message']['content']
        chat_memory[user_id].append({"role": "assistant", "content": reply})
        await update.message.reply_text(reply)
    else:
        await update.message.reply_text("❌ Error: DeepSeek API failed.")

    save_chat()

# 📁 Handle file uploads
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = update.message.document or (update.message.photo[-1] if update.message.photo else None)
    if not file:
        return await update.message.reply_text("❌ Unsupported file type.")

    file_path = f"downloads/{file.file_unique_id}"
    os.makedirs("downloads", exist_ok=True)
    telegram_file = await file.get_file()
    await telegram_file.download_to_drive(file_path)

    await update.message.reply_text(f"📁 File received: {file.file_name if hasattr(file, 'file_name') else 'image'}")

# 🔄 Handle /reset command
async def reset_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_memory.pop(user_id, None)
    save_chat()
    await update.message.reply_text("🧠 Your chat history has been cleared. Start fresh!")

# 🚀 Start the Telegram bot
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("reset", reset_chat))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, handle_file))

print("🚀 Bot is running...")
app.run_polling()
