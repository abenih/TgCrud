from sqlalchemy.future import select
from sqlalchemy import update
from src.db import SessionLocal
from src.models import Note

async def create_note(user_id: int, title: str, content: str):
    async with SessionLocal() as session:
        note = Note(user_id=user_id, title=title, content=content)
        session.add(note)
        await session.commit()
        await session.refresh(note)
        return note

async def get_user_notes(user_id: int):
    async with SessionLocal() as session:
        result = await session.execute(
            select(Note).filter_by(user_id=user_id).order_by(Note.updated_at.desc())
        )
        return result.scalars().all()

async def get_note_by_id(note_id: int, user_id: int):
    async with SessionLocal() as session:
        result = await session.execute(
            select(Note).filter_by(id=note_id, user_id=user_id)
        )
        return result.scalar()

async def update_note(note_id: int, user_id: int, title: str, content: str):
    async with SessionLocal() as session:
        stmt = (
            update(Note)
            .where(Note.id == note_id, Note.user_id == user_id)
            .values(title=title, content=content)
        )
        await session.execute(stmt)
        await session.commit()
        return await get_note_by_id(note_id, user_id)

async def delete_note(note_id: int, user_id: int):
    async with SessionLocal() as session:
        note = await get_note_by_id(note_id, user_id)
        if note:
            await session.delete(note)
            await session.commit()
            return True
        return False
