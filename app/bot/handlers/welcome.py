from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from ..keyboards.settings_menu import welcome_settings_keyboard

class WelcomeStates(StatesGroup):
    editing_text = State()
    waiting_custom_delay = State()

router = Router()

@router.callback_query(F.data.startswith('settings:welcome:'))
async def welcome_settings_callback(callback: CallbackQuery, chat_repo):
    chat_id = int(callback.data.split(':')[2])
    chat = await chat_repo.get(chat_id)
    if not chat:
        return await callback.answer("Chat not found.")
        
    settings = chat.get('welcome_settings', {
        'enabled': False,
        'trigger': 'on_approval',
        'delay': 0,
        'text': 'Welcome to the channel!'
    })
    
    await callback.message.edit_text(
        "👋 <b>Welcome Settings</b>\n\nConfigure welcome messages for new users.",
        reply_markup=welcome_settings_keyboard(
            chat_id=chat_id,
            welcome_enabled=settings.get('enabled', False),
            trigger=settings.get('trigger', 'on_approval'),
            delay_seconds=settings.get('delay', 0)
        )
    )

@router.callback_query(F.data.startswith('welcome:toggle:'))
async def toggle_welcome(callback: CallbackQuery, chat_repo):
    chat_id = int(callback.data.split(':')[2])
    chat = await chat_repo.get(chat_id)
    settings = chat.get('welcome_settings', {})
    
    settings['enabled'] = not settings.get('enabled', False)
    await chat_repo.update_settings(chat_id, {'welcome_settings': settings})
    
    await callback.message.edit_reply_markup(
        reply_markup=welcome_settings_keyboard(
            chat_id=chat_id,
            welcome_enabled=settings['enabled'],
            trigger=settings.get('trigger', 'on_approval'),
            delay_seconds=settings.get('delay', 0)
        )
    )

@router.callback_query(F.data.startswith('welcome:trigger:'))
async def set_welcome_trigger(callback: CallbackQuery, chat_repo):
    parts = callback.data.split(':')
    chat_id = int(parts[2])
    trigger = parts[3]
    
    chat = await chat_repo.get(chat_id)
    settings = chat.get('welcome_settings', {})
    settings['trigger'] = trigger
    await chat_repo.update_settings(chat_id, {'welcome_settings': settings})
    
    await callback.message.edit_reply_markup(
        reply_markup=welcome_settings_keyboard(
            chat_id=chat_id,
            welcome_enabled=settings.get('enabled', False),
            trigger=trigger,
            delay_seconds=settings.get('delay', 0)
        )
    )

@router.callback_query(F.data.startswith('welcome:edit_text:'))
async def start_edit_welcome_text(callback: CallbackQuery, state: FSMContext):
    chat_id = int(callback.data.split(':')[2])
    await state.set_state(WelcomeStates.editing_text)
    await state.update_data(chat_id=chat_id)
    
    await callback.message.answer(
        "Please send the new welcome message text.\n"
        "You can use HTML formatting."
    )
    await callback.answer()

@router.message(WelcomeStates.editing_text)
async def receive_welcome_text(message: Message, state: FSMContext, chat_repo):
    if not message.text:
        return await message.answer("Please send text.")
        
    data = await state.get_data()
    chat_id = data['chat_id']
    
    chat = await chat_repo.get(chat_id)
    settings = chat.get('welcome_settings', {})
    settings['text'] = message.html_text
    await chat_repo.update_settings(chat_id, {'welcome_settings': settings})
    
    await state.clear()
    await message.answer("✅ Welcome text updated!")

@router.callback_query(F.data.startswith('welcome:preview:'))
async def preview_welcome(callback: CallbackQuery, chat_repo):
    chat_id = int(callback.data.split(':')[2])
    chat = await chat_repo.get(chat_id)
    settings = chat.get('welcome_settings', {})
    text = settings.get('text', 'Welcome!')
    
    await callback.message.answer(f"<b>Preview:</b>\n\n{text}")
    await callback.answer()
