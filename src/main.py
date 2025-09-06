import asyncio
import sys
from telegram.ext import ApplicationBuilder
from src.config import BOT_TOKEN, ADMIN_ID
from src.handlers import get_handlers
from src.db import engine, Base

# Cross-platform event loop fix
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def main():
    # Create database tables if not exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Build the Telegram bot
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add all handlers
    print("DEBUG: Adding handlers...")
    for handler in get_handlers():
        print(f"DEBUG: Adding handler: {type(handler).__name__}")
        app.add_handler(handler)
    print("DEBUG: All handlers added successfully")

    print("Bot is running...")
    print("DEBUG: Bot initialized and starting...")
    
    # Initialize and start the bot
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    print("DEBUG: Bot is now polling for updates...")
    
    # Keep the bot running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

async def start(update, context):
    """Handle /start command and set admin if not already set"""
    # Set admin if not yet assigned
    if ADMIN_ID is None:
        ADMIN_ID = update.effective_user.id
        await update.message.reply_text("You are now set as the admin.")
    else:
        await update.message.reply_text("Welcome back!")
    
    # Continue with normal start logic
    # ...existing start logic...

if __name__ == "__main__":
    # Simple async execution
    asyncio.run(main())
