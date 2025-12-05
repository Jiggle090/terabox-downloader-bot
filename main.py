import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters

BOT_TOKEN = "8010597644:AAGiz57xHENfGp85jB8LlIumf-2ydfFxgdAE"
FREE_CREDITS = 3
API_URL = "https://teraboxapi.com/api?url="

user_credits = {}

async def start(update, context):
    user_id = update.effective_user.id
    if user_id not in user_credits:
        user_credits[user_id] = FREE_CREDITS

    await update.message.reply_text(
        f"Welcome!\nFree credits: {user_credits[user_id]}\nSend a TeraBox link."
    )

async def handle(update, context):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id not in user_credits:
        user_credits[user_id] = FREE_CREDITS

    if user_credits[user_id] <= 0:
        await update.message.reply_text("No free credits left.")
        return

    if "terabox" not in text and "1024tera" not in text:
        await update.message.reply_text("Send a valid TeraBox link.")
        return

    await update.message.reply_text("Processing your link...")

    try:
        data = requests.get(API_URL + text).json()
    except:
        await update.message.reply_text("API Error.")
        return

    if not data.get("status"):
        await update.message.reply_text("Failed to extract video.")
        return

    direct = data.get("download")
    title = data.get("title", "Video")
    size = data.get("size", "Unknown")

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Fast Download", url=direct)]
    ])

    sent = False

    if "MB" in size:
        try:
            mb = float(size.replace("MB", "").strip())
            if mb <= 50:
                await context.bot.send_video(
                    chat_id=update.effective_chat.id,
                    video=direct,
                    caption=f"{title}\nSize: {size}",
                    reply_markup=markup
                )
                sent = True
        except:
            pass

    if not sent:
        await update.message.reply_text(
            f"Title: {title}\nSize: {size}\nClick below to download:",
            reply_markup=markup
        )

    user_credits[user_id] -= 1
    await update.message.reply_text(
        f"Remaining credits: {user_credits[user_id]}"
    )


app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

app.run_polling()
