from telegram.ext import ContextTypes
from .db import SessionLocal
from .models import User

async def list_users(update, context: ContextTypes.DEFAULT_TYPE):
    session = SessionLocal()
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()

    if not user or not user.is_admin:
        await update.message.reply_text("You are not admin.")
        return

    users = session.query(User).all()
    msg = "Registered Users:\n"
    for u in users:
        msg += f"{u.id}: {u.phone} (Admin: {u.is_admin})\n"
    await update.message.reply_text(msg)
