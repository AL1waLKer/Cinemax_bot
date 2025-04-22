import os
import logging
from datetime import datetime
from typing import Optional, List

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=os.getenv("BOT_TOKEN"))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Database setup
Base = declarative_base()
engine = create_engine('sqlite:///bot.db')
Session = sessionmaker(bind=engine)

# Database models
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True)
    username = Column(String)
    role = Column(String, default='user')  # superadmin, admin, user
    secret_code = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Video(Base):
    __tablename__ = 'videos'
    
    id = Column(Integer, primary_key=True)
    file_id = Column(String, unique=True)
    title = Column(String)
    uploaded_by = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.utcnow)

class Channel(Base):
    __tablename__ = 'channels'
    
    id = Column(Integer, primary_key=True)
    channel_id = Column(String, unique=True)
    title = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class ActionLog(Base):
    __tablename__ = 'action_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    action = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

# Create tables
Base.metadata.create_all(engine)

# States
class UserStates(StatesGroup):
    waiting_for_secret_code = State()
    waiting_for_channel_id = State()
    waiting_for_video = State()
    waiting_for_video_title = State()

# Helper functions
async def check_subscription(user_id: int, channel_id: str) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        return member.status not in ['left', 'kicked']
    except Exception as e:
        logging.error(f"Obuna tekshirishda xatolik: {e}")
        return False

async def log_action(user_id: int, action: str):
    session = Session()
    try:
        log = ActionLog(user_id=user_id, action=action)
        session.add(log)
        session.commit()
    finally:
        session.close()

# Command handlers
@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await message.delete()
    await state.set_state(UserStates.waiting_for_secret_code)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Maxfiy kodni kiriting", callback_data="enter_code")]
    ])
    
    await message.answer(
        "Cinemax botiga xush kelibsiz! Kontentga kirish uchun maxfiy kodni kiriting.",
        reply_markup=keyboard
    )

@dp.message(Command("id"))
async def cmd_id(message: Message):
    await message.answer(f"Sizning ID raqamingiz: {message.from_user.id}")

# Callback handlers
@dp.callback_query(F.data == "enter_code")
async def process_code_entry(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Iltimos, maxfiy kodni yuboring:",
        reply_markup=None
    )
    await state.set_state(UserStates.waiting_for_secret_code)

# Main function
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 