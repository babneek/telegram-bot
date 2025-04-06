import datetime
import asyncio
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ==== CONFIG ====
BOT_TOKEN = "7740623914:AAFUcxpHgWyaHvplwB17Uy6jw5ypDdA6McI"
CHANNEL_ID = -1002384289961
UPI_QR_PATH = "upi_qr.png"
INVITE_LINK = "https://t.me/+taeC5o_jA941M2E0"
UPI_ID = "paytmqrslhta2csqu@paytm"
YOUR_ADMIN_ID = 6624127069

# Track users and their subscription expiry
users = {}

# ==== START COMMAND ====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Pay Now", callback_data='pay')],
        [InlineKeyboardButton("I Have Paid", callback_data='paid')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome! Choose an option:", reply_markup=reply_markup)

# ==== BUTTON HANDLER ====

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "pay":
        caption = (
            f"Pay ₹169 using UPI\n"
            f"Scan the QR code or copy the UPI ID below:\n\n"
            f"`{UPI_ID}`\n\n"
            f"After payment, click 'I Have Paid'."
        )
        await query.message.reply_photo(
            photo=open(UPI_QR_PATH, "rb"),
            caption=caption,
            parse_mode="Markdown",
        )

    elif query.data == "paid":
        await query.message.reply_text("Please send your payment screenshot for manual verification.")

# ==== HANDLE SCREENSHOT ====

async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user

    if update.message.photo:
        await update.message.reply_text("Thanks! Your payment will be verified soon.")
        photo_file = update.message.photo[-1].file_id
        caption = (
            f"Payment Screenshot Received\n"
            f"From: @{user.username or 'NoUsername'}\n"
            f"User ID: `{user.id}`"
        )
        await context.bot.send_photo(chat_id=YOUR_ADMIN_ID, photo=photo_file, caption=caption, parse_mode="Markdown")
    else:
        await update.message.reply_text("Please send a valid screenshot of your payment.")

# ==== SUBSCRIPTION REMINDER ====

async def subscription_reminder(user_id, expiry, context):
    reminder_time = expiry - datetime.timedelta(days=1)
    wait_time = (reminder_time - datetime.datetime.now()).total_seconds()

    if wait_time > 0:
        await asyncio.sleep(wait_time)

    await context.bot.send_message(
        chat_id=user_id,
        text=f"⏰ Reminder: Your subscription expires on {expiry.strftime('%d %b %Y')}.\n"
             f"Please renew to continue access."
    )

# ==== AUTO-KICK AFTER EXPIRY ====

async def subscription_expiry_check(user_id, expiry, context):
    wait_time = (expiry - datetime.datetime.now()).total_seconds()
    if wait_time > 0:
        await asyncio.sleep(wait_time)

    if users.get(user_id) == expiry:
        try:
            await context.bot.ban_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
            await context.bot.unban_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
            await context.bot.send_message(
                chat_id=user_id,
                text="⛔ Your subscription has expired. You’ve been removed from the channel."
            )
            users.pop(user_id, None)
        except Exception as e:
            print(f"Error kicking user {user_id}: {e}")

# ==== VERIFY COMMAND ====

async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text("Usage: /verify user_id")
        return

    try:
        user_id = int(context.args[0])
        expiry = datetime.datetime.now() + datetime.timedelta(days=30)
        users[user_id] = expiry

        await update.message.reply_text(f"✅ User ID {user_id} verified until {expiry.strftime('%d %b %Y')}.")

        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ You’ve been verified!\nAccess expires on {expiry.strftime('%d %b %Y')}.\n\n"
                 f"Here’s your private channel link:\n{INVITE_LINK}"
        )

        context.application.create_task(subscription_reminder(user_id, expiry, context))
        context.application.create_task(subscription_expiry_check(user_id, expiry, context))

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

# ==== MAIN ====

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("verify", verify))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_screenshot))

    print("Bot is running...")
    app.run_polling()