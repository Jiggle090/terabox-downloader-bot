import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = "8010597644:AAEsrJEz51DraEyLI2f1NUUH3KQUn7FtE1Y"
FREE_CREDITS = 3

TERABOX_API = "https://teraboxapi.com/api?url="     # working API

user_credits = {}

async def start(update, context):
    user_id = update.effective_user.id
    if user_id not in user_credits:
        user_credits[user_id] = FREE_CREDITS

    await update.message.reply_text(
        f"👋 Welcome!\n🎁 Free credits: {user_credits[user_id]}\nSend any TeraBox link!"
    )


async def handle(update, context):
    user_id = update.effective_user.id
    text = update.message.text

    # Credits check
    if user_id not in user_credits:
        user_credits[user_id] = FREE_CREDITS

    if user_credits[user_id] <= 0:
        return await update.message.reply_text("❌ No free credits left!")

    # Validate link
    if "terabox" not in text and "1024tera" not in text:
        return await update.message.reply_text("❗ Please send a valid TeraBox link.")

    await update.message.reply_text("⏳ Fetching download link...")

    # Call API
    try:
        result = requests.get(TERABOX_API + text).json()
    except:
        return await update.message.reply_text("❌ API Error. Try again.")

    if result.get("status") != True:
        return await update.message.reply_text("❌ Could not extract video. Link invalid or protected.")

    # Extract info
    direct_url = result.get("download")
    title = result.get("title", "TeraBox Video")
    size = result.get("size", "Unknown")
    thumb = result.get("thumbnail")

    # Create buttons
    buttons = [
        [InlineKeyboardButton("🔥 Fast Download 🔥", url=direct_url)]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    # Try sending video if small
    try:
        if "MB" in size and float(size.replace("MB", "").strip()) <= 50:
            await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=direct_url,
                caption=f"🎬 {title}\n📏 Size: {size}",
                reply_markup=reply_markup
            )
        else:
            raise Exception("Large file")
    except:
        msg = (
            f"🎬 *{title}*\n"
            f"📏 Size: {size}\n\n"
            f"Click below to download:"
        )
        await update.message.reply_markdown(msg, reply_markup=reply_markup)

    # Reduce credit
    user_credits[user_id] -= 1
    await update.message.reply_text(f"✅ Done! Remaining credits: {user_credits[user_id]}")


# Build bot
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

app.run_polling()
        # Some APIs wrap data inside "data" key
        info = data.get("data", data)

        direct_url = (
            info.get("download_url")
            or info.get("url")
            or info.get("link")
            or info.get("download")
        )
        if not direct_url:
            return None

        filename = info.get("filename") or info.get("title") or "Video"
        size = info.get("size") or info.get("filesize") or info.get("file_size")
        thumb = info.get("thumbnail") or info.get("thumb") or info.get("poster")

        return {
            "direct_url": direct_url,
            "filename": filename,
            "size": size,
            "thumb": thumb,
        }

    except Exception as e:
        print("Error calling API:", e)
        return None


# ───────── HELPER: TRY BOTH APIS ─────────
def get_terabox_info(url):
    """
    Tries API_1 first, if fails then API_2.
    Returns dict or None.
    """
    info = call_single_api(API_1, url)
    if info:
        return info

    info = call_single_api(API_2, url)
    return info


# ───────── COMMAND: /start ─────────
async def start(update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_credits:
        user_credits[user_id] = FREE_CREDITS

    await update.message.reply_text(
        f"👋 Welcome!\n"
        f"🎁 Free credits: {user_credits[user_id]}\n\n"
        f"Send me a Terabox link and I’ll fetch the video for you."
    )


# ───────── MESSAGE HANDLER ─────────
async def handle_message(update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = (update.message.text or "").strip()

    # Give default credits if new user
    if user_id not in user_credits:
        user_credits[user_id] = FREE_CREDITS

    # If no credits left
    if user_credits[user_id] <= 0:
        await update.message.reply_text(
            "❌ Your free credits are finished.\n"
            "Later we’ll add shortlink unlock here 😊"
        )
        return

    # Very simple Terabox link detection
    if "terabox" not in text and "1024tera" not in text:
        await update.message.reply_text(
            "❓ This doesn’t look like a Terabox link.\n"
            "Please send a valid Terabox video link."
        )
        return

    # Tell user we are processing
    await update.message.reply_text("⏳ Processing your Terabox link, please wait...")

    # Call APIs (blocking, but okay for simple bot)
    info = get_terabox_info(text)

    if not info:
        await update.message.reply_text(
            "❌ Failed to fetch download info.\n"
            "Terabox server might be busy or link is invalid."
        )
        return

    direct_url = info["direct_url"]
    filename = info["filename"]
    size_raw = info["size"]
    thumb = info["thumb"]

    size_mb = parse_size_mb(size_raw)
    size_text = f"{size_mb:.2f} MB" if size_mb is not None else str(size_raw or "Unknown size")

    # Build buttons
    keyboard = [
        [InlineKeyboardButton("🔥 Fast Download 🔥", url=direct_url)],
        [InlineKeyboardButton("💚 Share this bot", url=SHARE_URL)],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # If file is reasonably small (<= 50MB) → try to send video
    small_enough = size_mb is not None and size_mb <= 50.0

    if small_enough:
        try:
            await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=direct_url,
                caption=f"🎬 {filename}\n📏 Size: {size_text}",
                reply_markup=reply_markup,
            )

            # Deduct credit only if sent successfully
            user_credits[user_id] -= 1

            await update.message.reply_text(
                f"✅ Video sent.\n"
                f"Remaining free credits: {user_credits[user_id]}"
            )
            return

        except Exception as e:
            # If sending video fails, fallback to link-only mode
            print("Error sending video, falling back to link only:", e)

    # If too big OR sending video failed → send info + buttons
    message_text = (
        f"🎬 *{filename}*\n"
        f"📏 Size: {size_text}\n\n"
        f"Here is your download link:"
    )

    await update.message.reply_markdown(
        message_text,
        reply_markup=reply_markup,
    )

    # Deduct credit
    user_credits[user_id] -= 1

    await update.message.reply_text(
        f"✅ Link sent.\n"
        f"Remaining free credits: {user_credits[user_id]}"
    )


# ───────── MAIN APP SETUP ─────────
app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

if __name__ == "__main__":
    app.run_polling()
