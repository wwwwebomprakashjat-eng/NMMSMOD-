import nest_asyncio
nest_asyncio.apply()

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import json, os, re
import asyncio
import logging

BOT_TOKEN = "8372436876:AAFFmGzNq5UegFdJN18YNcijiO-Gd75HI68"
ADMIN_ID = 7000109688

user_demo_status = {"type_1": [], "type_2": []}
allowed_users = set()

# Load demo status
if os.path.exists("demo_status.json"):
    with open("demo_status.json", "r") as f:
        data = json.load(f)
        user_demo_status = data if isinstance(data, dict) and "type_1" in data else {"type_1": [], "type_2": []}

# Load allowed users
if os.path.exists("allowed_users.json"):
    with open("allowed_users.json", "r") as f:
        allowed_users = set(json.load(f))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔸 𝐓𝐲𝐩𝐞 𝟏", callback_data="type_1")],
        [InlineKeyboardButton("🔹 𝐓𝐲𝐩𝐞 𝟐", callback_data="type_2")]
    ]
    message = """📲 𝐍𝐌𝐌𝐒 𝐌𝐎𝐃 —
Choose one

🔸 𝐓𝐲𝐩𝐞 𝟏:
   𝐖𝐨𝐫𝐤𝐞𝐫𝐬 𝐜𝐨𝐮𝐧𝐭 𝐫𝐞𝐦𝐨𝐯𝐞
   𝐃𝐞𝐯𝐞𝐥𝐨𝐩𝐞𝐫 𝐨𝐩𝐭𝐢𝐨𝐧𝐬 𝐛𝐲𝐩𝐚𝐬𝐬
   𝐅𝐚𝐜𝐤 𝐥𝐨𝐜𝐚𝐭𝐢𝐨𝐧 𝐛𝐲𝐩𝐚𝐬𝐬
   𝐓𝐢𝐦𝐞 𝐜𝐡𝐚𝐧𝐠𝐞 𝐞𝐧𝐚𝐛𝐥𝐞

🔹 𝐓𝐲𝐩𝐞 𝟐:
   𝐆𝐚𝐥𝐥𝐞𝐫𝐲 𝐩𝐡𝐨𝐭𝐨 𝐮𝐩𝐥𝐨𝐚𝐝
   𝐃𝐞𝐯𝐞𝐥𝐨𝐩𝐞𝐫 𝐨𝐩𝐭𝐢𝐨𝐧 𝐛𝐲𝐩𝐚𝐬𝐬
   𝐅𝐚𝐜𝐤 𝐥𝐨𝐜𝐚𝐭𝐢𝐨𝐧 𝐛𝐲𝐩𝐚𝐬𝐬
   𝐓𝐢𝐦𝐞 𝐜𝐡𝐚𝐧𝐠𝐞"""
    await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_id = user.id
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    username = f"@{user.username}" if user.username else "NoUsername"
    data = query.data

    if data in ["type_1", "type_2"]:
        price_text = "Half Month: ₹1000\nFull Month: ₹2000\nDemo: Free" if data == "type_1" else "Half Month: ₹1500\nFull Month: ₹2500\nDemo: Free"
        plan_keyboard = [
            [InlineKeyboardButton("Half Month", callback_data=f"half_{data}")],
            [InlineKeyboardButton("Full Month", callback_data=f"full_{data}")],
            [InlineKeyboardButton("Demo", callback_data=f"demo_{data}")]
        ]
        await query.edit_message_text(
            f"Choose plan for {data.replace('_', ' ').title()}:\n{price_text}",
            reply_markup=InlineKeyboardMarkup(plan_keyboard)
        )

    elif data.startswith("demo"):
        demo_type = data.split("_", 1)[1]
        demo_name = "Type 1" if demo_type == "type_1" else "Type 2"

        if user_id in user_demo_status[demo_type]:
            await query.edit_message_text(f"❌ {demo_name} Demo already taken.")
        else:
            user_demo_status[demo_type].append(user_id)
            with open("demo_status.json", "w") as f:
                json.dump(user_demo_status, f)

            await query.edit_message_text(f"⏳ Please wait while we set up your {demo_name} demo...")
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    f"👤 <b>{full_name}</b> ({username})\n"
                    f"📱 ID: <code>{user_id}</code>\n"
                    f"🎁 Requested: <b>{demo_name} Demo</b>"
                ),
                parse_mode="HTML",
                reply_markup=ForceReply()
            )

    elif data.startswith("half") or data.startswith("full"):
        plan = "Half Month" if data.startswith("half") else "Full Month"
        mod_type = "Type 1" if "type_1" in data else "Type 2"

        await query.edit_message_text(f"✅ You selected {plan} for {mod_type}. Please wait...")
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"👤 <b>{full_name}</b> ({username})\n"
                f"📱 ID: <code>{user_id}</code>\n"
                f"💰 Order: <b>{plan} for {mod_type}</b>"
            ),
            parse_mode="HTML",
            reply_markup=ForceReply()
        )

# Admin reply handler (grants access to user)
async def admin_reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        original = update.message.reply_to_message.text
        match = re.search(r"ID: (\d+)", original)
        if match:
            user_id = int(match.group(1))

            allowed_users.add(user_id)
            with open("allowed_users.json", "w") as f:
                json.dump(list(allowed_users), f)

            if update.message.text:
                await context.bot.send_message(chat_id=user_id, text=f"📩 Admin: {update.message.text}")

            if update.message.document or update.message.photo or update.message.video:
                await context.bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=update.message.chat_id,
                    message_id=update.message.message_id
                )

            await update.message.reply_text("✅ Sent and access granted.")
        else:
            await update.message.reply_text("❌ Could not extract user ID.")

# Block unauthorized users from messaging first
async def user_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in allowed_users:
        await update.message.reply_text("❌ You cannot message first. Please wait for admin reply.")
        return

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📨 Message from <b>{update.message.from_user.full_name}</b>\n🆔 <code>{user_id}</code>\n\n{update.message.text}",
        parse_mode="HTML"
    )

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot setup
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_click))
app.add_handler(MessageHandler(filters.REPLY & filters.ALL, admin_reply_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, user_message_handler))

# Run loop
async def main():
    try:
        await app.initialize()
        await app.start()
        logger.info("🤖 NMMS Bot started...")
        await app.updater.start_polling(drop_pending_updates=True)
        await asyncio.Event().wait()
    except Exception as e:
        logger.error(f"Error: {e}")
        await asyncio.sleep(10)
        await main()

if __name__ == "__main__":
    while True:
        try:
            asyncio.run(main())
        except Exception as e:
            print(f"Restarting due to error: {e}")
            import time
            time.sleep(10)
