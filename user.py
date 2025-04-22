from aiogram import types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import Session

from bot import dp, bot, Session, User, Video, Channel, check_subscription, log_action, UserStates

# Helper functions
async def get_user_videos():
    session = Session()
    try:
        return session.query(Video).all()
    finally:
        session.close()

async def get_required_channels():
    session = Session()
    try:
        return session.query(Channel).all()
    finally:
        session.close()

async def verify_user_access(user_id: int, secret_code: str) -> bool:
    session = Session()
    try:
        user = session.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            user = User(telegram_id=user_id, secret_code=secret_code)
            session.add(user)
            session.commit()
        return user.secret_code == secret_code
    finally:
        session.close()

# Message handlers
@dp.message(UserStates.waiting_for_secret_code)
async def process_secret_code(message: types.Message, state: FSMContext):
    await message.delete()
    
    if not await verify_user_access(message.from_user.id, message.text):
        await message.answer("Noto'g'ri maxfiy kod. Iltimos, qaytadan urinib ko'ring.")
        return

    # Check channel subscriptions
    channels = await get_required_channels()
    if not channels:
        # No channels required, proceed to show content
        await show_content(message)
        return

    not_subscribed = []
    for channel in channels:
        if not await check_subscription(message.from_user.id, channel.channel_id):
            not_subscribed.append(channel)

    if not_subscribed:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=channel.title, url=f"https://t.me/{channel.channel_id}")]
            for channel in not_subscribed
        ])
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text="Men obuna bo'ldim", callback_data="check_subscription")
        ])
        
        await message.answer(
            "Kontentga kirish uchun quyidagi kanallarga obuna bo'ling:",
            reply_markup=keyboard
        )
        return

    await show_content(message)

async def show_content(message: types.Message):
    videos = await get_user_videos()
    if not videos:
        await message.answer("Hozircha videolar mavjud emas.")
        return

    for video in videos:
        await message.answer_video(
            video=video.file_id,
            caption=video.title,
            protect_content=True
        )

@dp.callback_query(F.data == "check_subscription")
async def check_subscriptions(callback: types.CallbackQuery):
    channels = await get_required_channels()
    not_subscribed = []
    
    for channel in channels:
        if not await check_subscription(callback.from_user.id, channel.channel_id):
            not_subscribed.append(channel)

    if not_subscribed:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=channel.title, url=f"https://t.me/{channel.channel_id}")]
            for channel in not_subscribed
        ])
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text="Men obuna bo'ldim", callback_data="check_subscription")
        ])
        
        await callback.message.edit_text(
            "Siz hali quyidagi kanallarga obuna bo'lmagansiz:",
            reply_markup=keyboard
        )
        return

    await callback.message.delete()
    await show_content(callback.message) 