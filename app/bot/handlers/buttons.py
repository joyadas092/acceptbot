from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from ..keyboards.button_builder import button_builder_keyboard, button_row_selector_keyboard

class ButtonBuilderStates(StatesGroup):
    waiting_button_text = State()
    waiting_button_url = State()
    waiting_button_row = State()

router = Router()

@router.callback_query(F.data.startswith('settings:buttons:'))
async def buttons_callback(callback: CallbackQuery, chat_repo):
    chat_id = int(callback.data.split(':')[2])
    chat = await chat_repo.get(chat_id)
    if not chat:
        return await callback.answer("Chat not found.")
        
    buttons = chat.get('welcome_buttons', [])
    
    await callback.message.edit_text(
        "🔘 <b>Button Builder</b>\n\nConfigure inline buttons for your welcome message.",
        reply_markup=button_builder_keyboard(chat_id, buttons)
    )

@router.callback_query(F.data.startswith('btn:add:'))
async def add_button_start(callback: CallbackQuery, state: FSMContext):
    chat_id = int(callback.data.split(':')[2])
    await state.set_state(ButtonBuilderStates.waiting_button_text)
    await state.update_data(chat_id=chat_id)
    
    await callback.message.answer("Please enter the text for the new button (max 32 chars):")
    await callback.answer()

@router.message(ButtonBuilderStates.waiting_button_text)
async def receive_button_text(message: Message, state: FSMContext):
    if not message.text:
        return await message.answer("Please send text.")
        
    await state.update_data(btn_text=message.text[:32])
    await state.set_state(ButtonBuilderStates.waiting_button_url)
    await message.answer("Now enter the URL for the button (must start with http:// or https://):")

@router.message(ButtonBuilderStates.waiting_button_url)
async def receive_button_url(message: Message, state: FSMContext, chat_repo):
    if not message.text or not message.text.startswith(('http://', 'https://')):
        return await message.answer("Invalid URL. Must start with http:// or https://")
        
    data = await state.get_data()
    chat_id = data['chat_id']
    btn_text = data['btn_text']
    btn_url = message.text
    
    chat = await chat_repo.get(chat_id)
    buttons = chat.get('welcome_buttons', [])
    
    existing_rows = [b.get('row', 1) for b in buttons]
    
    await state.update_data(btn_url=btn_url)
    await state.set_state(ButtonBuilderStates.waiting_button_row)
    
    await message.answer(
        "Select which row to place this button in:",
        reply_markup=button_row_selector_keyboard(chat_id, existing_rows)
    )

@router.callback_query(F.data.startswith('btn:row:'))
async def set_button_row(callback: CallbackQuery, state: FSMContext, chat_repo):
    parts = callback.data.split(':')
    chat_id = int(parts[2])
    row = int(parts[3])
    
    data = await state.get_data()
    btn_text = data.get('btn_text')
    btn_url = data.get('btn_url')
    
    if not btn_text:
        await state.clear()
        return await callback.message.answer("Session expired. Please try again.")
        
    chat = await chat_repo.get(chat_id)
    buttons = chat.get('welcome_buttons', [])
    buttons.append({'text': btn_text, 'url': btn_url, 'row': row})
    await chat_repo.update_settings(chat_id, {'welcome_buttons': buttons})
    
    await state.clear()
    
    await callback.message.edit_text(
        "✅ <b>Button added successfully!</b>",
        reply_markup=button_builder_keyboard(chat_id, buttons)
    )

@router.callback_query(F.data.startswith('btn:delete:'))
async def delete_button(callback: CallbackQuery, chat_repo):
    parts = callback.data.split(':')
    chat_id = int(parts[2])
    idx = int(parts[3])
    
    chat = await chat_repo.get(chat_id)
    buttons = chat.get('welcome_buttons', [])
    
    if 0 <= idx < len(buttons):
        buttons.pop(idx)
        await chat_repo.update_settings(chat_id, {'welcome_buttons': buttons})
        
    await callback.message.edit_reply_markup(
        reply_markup=button_builder_keyboard(chat_id, buttons)
    )
