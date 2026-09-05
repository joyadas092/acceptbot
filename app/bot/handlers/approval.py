from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from ..keyboards.settings_menu import approval_settings_keyboard

class ApprovalStates(StatesGroup):
    waiting_custom_delay = State()

router = Router()

@router.callback_query(F.data.startswith('settings:approval:'))
async def approval_settings_callback(callback: CallbackQuery, chat_repo):
    chat_id = int(callback.data.split(':')[2])
    chat = await chat_repo.get(chat_id)
    if not chat:
        return await callback.answer("Chat not found.")
        
    settings = chat.get('approval_settings', {'enabled': True, 'delay': 0})
    
    await callback.message.edit_text(
        "⚡ <b>Approval Settings</b>\n\nConfigure how join requests are handled.",
        reply_markup=approval_settings_keyboard(
            chat_id=chat_id,
            auto_approval=settings.get('enabled', True),
            delay_seconds=settings.get('delay', 0)
        )
    )

@router.callback_query(F.data.startswith('approval:toggle:'))
async def toggle_auto_approval(callback: CallbackQuery, chat_repo):
    chat_id = int(callback.data.split(':')[2])
    chat = await chat_repo.get(chat_id)
    settings = chat.get('approval_settings', {'enabled': True, 'delay': 0})
    
    settings['enabled'] = not settings['enabled']
    await chat_repo.update_settings(chat_id, {'approval_settings': settings})
    
    await callback.message.edit_reply_markup(
        reply_markup=approval_settings_keyboard(
            chat_id=chat_id,
            auto_approval=settings['enabled'],
            delay_seconds=settings['delay']
        )
    )

@router.callback_query(F.data.startswith('approval:delay:'))
async def set_approval_delay(callback: CallbackQuery, chat_repo, state: FSMContext):
    parts = callback.data.split(':')
    chat_id = int(parts[2])
    val = parts[3]
    
    if val == 'custom':
        await state.set_state(ApprovalStates.waiting_custom_delay)
        await state.update_data(chat_id=chat_id)
        await callback.message.answer("Enter custom delay in minutes (e.g. 10):")
        await callback.answer()
        return
        
    delay_seconds = int(val)
    chat = await chat_repo.get(chat_id)
    settings = chat.get('approval_settings', {'enabled': True, 'delay': 0})
    settings['delay'] = delay_seconds
    await chat_repo.update_settings(chat_id, {'approval_settings': settings})
    
    await callback.message.edit_reply_markup(
        reply_markup=approval_settings_keyboard(
            chat_id=chat_id,
            auto_approval=settings['enabled'],
            delay_seconds=delay_seconds
        )
    )

@router.message(ApprovalStates.waiting_custom_delay)
async def receive_custom_delay(message: Message, state: FSMContext, chat_repo):
    if not message.text or not message.text.isdigit():
        return await message.answer("Please enter a valid number of minutes.")
        
    minutes = int(message.text)
    delay_seconds = minutes * 60
    
    data = await state.get_data()
    chat_id = data['chat_id']
    
    chat = await chat_repo.get(chat_id)
    settings = chat.get('approval_settings', {'enabled': True, 'delay': 0})
    settings['delay'] = delay_seconds
    await chat_repo.update_settings(chat_id, {'approval_settings': settings})
    
    await state.clear()
    
    await message.answer(
        f"✅ Custom delay set to {minutes} minutes.",
        reply_markup=approval_settings_keyboard(
            chat_id=chat_id,
            auto_approval=settings['enabled'],
            delay_seconds=delay_seconds
        )
    )
