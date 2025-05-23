from aiogram import types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.orm import Session

from bot import dp, bot, Session, User, Video, Channel, ActionLog, check_subscription, log_action

# Admin States
class AdminStates(StatesGroup):
    waiting_for_admin_id = State()
    waiting_for_channel_id = State()
    waiting_for_video = State()
    waiting_for_video_title = State()

# Helper functions for admin operations
async def is_admin(user_id: int) -> bool:
    session = Session()
    try:
        user = session.query(User).filter(User.telegram_id == user_id).first()
        return user and user.role in ['admin', 'superadmin']
    finally:
        session.close()

async def is_superadmin(user_id: int) -> bool:
    session = Session()
    try:
        user = session.query(User).filter(User.telegram_id == user_id).first()
        return user and user.role == 'superadmin'
    finally:
        session.close()

# Admin panel commands
@dp.message(Command("panel"))
async def admin_panel(message: types.Message):
    if not await is_admin(message.from_user.id):
        await message.answer("Sizda admin paneliga kirish huquqi yo'q.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Video yuklash", callback_data="upload_video")],
        [InlineKeyboardButton(text="Videoni o'chirish", callback_data="delete_video")],
        [InlineKeyboardButton(text="Majburiy kanallarni o'rnatish", callback_data="set_channels")],
        [InlineKeyboardButton(text="Foydalanuvchilarga xabar yuborish", callback_data="send_post")]
    ])

    if await is_superadmin(message.from_user.id):
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text="Adminlarni boshqarish", callback_data="manage_admins")
        ])

    await message.answer("Admin panel:", reply_markup=keyboard)

# Superadmin panel
@dp.message(Command("spanel"))
async def superadmin_panel(message: types.Message):
    if not await is_superadmin(message.from_user.id):
        await message.answer("Sizda superadmin paneliga kirish huquqi yo'q.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Admin qo'shish", callback_data="add_admin")],
        [InlineKeyboardButton(text="Adminni o'chirish", callback_data="remove_admin")],
        [InlineKeyboardButton(text="Video yuklash", callback_data="upload_video")],
        [InlineKeyboardButton(text="Majburiy kanallarni o'rnatish", callback_data="set_channels")],
        [InlineKeyboardButton(text="Bot ma'lumotlarini tahrirlash", callback_data="edit_bot_info")],
        [InlineKeyboardButton(text="Videoni o'chirish", callback_data="delete_video")],
        [InlineKeyboardButton(text="Admin harakatlari jurnalini ko'rish", callback_data="view_logs")]
    ])

    await message.answer("Superadmin panel:", reply_markup=keyboard)

# Callback handlers for admin actions
@dp.callback_query(F.data == "upload_video")
async def process_upload_video(callback: types.CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Sizda video yuklash huquqi yo'q.")
        return

    await callback.message.edit_text(
        "Iltimos, video faylini yuboring:",
        reply_markup=None
    )
    await state.set_state(AdminStates.waiting_for_video)

@dp.callback_query(F.data == "set_channels")
async def process_set_channels(callback: types.CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Sizda kanallarni o'rnatish huquqi yo'q.")
        return

    await callback.message.edit_text(
        "Iltimos, kanal ID raqamini yuboring:",
        reply_markup=None
    )
    await state.set_state(AdminStates.waiting_for_channel_id)

# Message handlers for admin states
@dp.message(AdminStates.waiting_for_video)
async def process_video_upload(message: types.Message, state: FSMContext):
    if not message.video:
        await message.answer("Iltimos, video faylini yuboring.")
        return

    session = Session()
    try:
        user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
        video = Video(
            file_id=message.video.file_id,
            title=message.video.file_name or "Nomsiz",
            uploaded_by=user.id
        )
        session.add(video)
        session.commit()
        
        await log_action(user.id, f"Video yuklandi: {video.title}")
        await message.answer("Video muvaffaqiyatli yuklandi!")
        
        # Send video with restricted permissions
        await message.answer_video(
            video=message.video.file_id,
            caption=video.title,
            protect_content=True
        )
    finally:
        session.close()
        await state.clear()

@dp.message(AdminStates.waiting_for_channel_id)
async def process_channel_set(message: types.Message, state: FSMContext):
    try:
        channel_id = message.text.strip()
        session = Session()
        try:
            channel = Channel(channel_id=channel_id)
            session.add(channel)
            session.commit()
            
            user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
            await log_action(user.id, f"Kanal qo'shildi: {channel_id}")
            
            await message.answer("Kanal muvaffaqiyatli qo'shildi!")
        finally:
            session.close()
    except Exception as e:
        await message.answer(f"Kanal qo'shishda xatolik: {str(e)}")
    
    await state.clear() 