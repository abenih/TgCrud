import asyncio
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Cross-platform event loop fix
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simple start command with inline keyboard"""
    print(f"DEBUG: Start command received from {update.effective_user.username}")
    
    keyboard = [
        [InlineKeyboardButton("Test Button", callback_data="test_button")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🧪 Test Bot\n\nPress the test button:",
        reply_markup=reply_markup
    )
    print("DEBUG: Test button displayed")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simple callback handler"""
    print("DEBUG: handle_callback function called!")
    query = update.callback_query
    print(f"DEBUG: Received callback: {query.data}")
    
    await query.answer("Button pressed!")
    await query.edit_message_text("✅ Button worked! Callback received successfully!")

async def main():
    # Get bot token from config
    from src.config import BOT_TOKEN
    
    # Build the bot
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Add handlers
    print("DEBUG: Adding handlers...")
    app.add_handler(CommandHandler("start", start))
    print("DEBUG: CommandHandler added")
    
    app.add_handler(CallbackQueryHandler(handle_callback))
    print("DEBUG: CallbackQueryHandler added")
    print("DEBUG: All handlers added successfully")
    
    print("Test bot is running...")
    print("DEBUG: Bot initialized and starting...")
    
    # Start the bot
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    print("DEBUG: Bot is now polling for updates...")
    
    # Keep running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())

