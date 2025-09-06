from sqlalchemy.future import select
from sqlalchemy import func
from src.db import SessionLocal
from src.models import User

async def get_user_by_telegram_id(telegram_id: str):
    async with SessionLocal() as session:
        result = await session.execute(select(User).filter_by(telegram_id=str(telegram_id)))
        return result.scalar()

async def create_user(telegram_id: str, username: str, is_admin: bool=False):
    async with SessionLocal() as session:
        # Check if this is the first user (make them admin)
        user_count = await session.execute(select(func.count(User.id)))
        is_first_user = user_count.scalar() == 0
        
        # If it's the first user, make them admin regardless of the is_admin parameter
        if is_first_user:
            is_admin = True
        
        user = User(telegram_id=telegram_id, username=username, is_admin=is_admin)
        session.add(user)
        await session.commit()
        return user

async def verify_pattern_lock(user_id: int, pattern: str):
    """Verify unlock by checking if the user is the admin."""
    from src.config import ADMIN_ID
    return user_id == ADMIN_ID
