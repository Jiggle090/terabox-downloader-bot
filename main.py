import re
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# ───────── CONFIG ─────────
BOT_TOKEN = "8010597644:AAEsrJEz51DraEyLI2f1NUUH3KQUn7FtE1Y"

# If you want the Share button to open your bot, put your bot link here:
SHARE_URL = "https://t.me/TeraDOWN9_bot"   # <- CHANGE THIS LATER

FREE_CREDITS = 3

# Two example TeraBox APIs (these may change in future – you can replace with your own)
API_1 = "https://tb.rip/api?url={url}"
API_2 = "https://api.terabox.tech/api/download?url={url}"
# ──────────────────────────

user_credits = {}  # user_id -> remaining credits


# ───────── HELPER: PARSE SIZE INTO MB ─────────
def parse_size_mb(size_value):
    """
    Tries to convert different 'size' formats into MB (float).
    Examples:
      "123.4 MB" -> 123.4
      "1.2 GB"   -> 1228.8
      10485760   -> 10.0 (bytes)
    Returns None if unknown.
    """
    if size_value is None:
        return None

    # If it's already a number (bytes assumed)
    if isinstance(size_value, (int, float)):
        # assume bytes
        return float(size_value) / (1024 * 1024)

    if isinstance(size_value, str):
        text = size_value.strip().lower()
        m = re.search(r"([\d.]+)", text)
        if not m:
            return None
        num = float(m.group(1))

        if "gb" in text:
            return num * 1024.0
        # assume MB by default
        return num

    return None


# ───────── HELPER: CALL A SINGLE API ─────────
def call_single_api(api_template, url):
    try:
        full_url = api_template.format(url=url)
        resp = requests.get(full_url, timeout=20)
        if resp.status_code != 200:
            print("API status code:", resp.status_code)
            return None

        data = resp.json()
        print("API response:", data)

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