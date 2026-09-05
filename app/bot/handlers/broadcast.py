from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import uuid

from ..keyboards.broadcast_menu import broadcast_target_keyboard, broadcast_confirm_keyboard, broadcast_control_keyboard

class BroadcastStates(StatesGroup):
    composing_message = State()
    selecting_target = State()
    confirming = State()

router = Router()

@router.message(Command('broadcast'))
async def broadcast_command(message: Message, state: FSMContext):
    # normally check entitlement here
    await state.set_state(BroadcastStates.composing_message)
    await message.answer("Please send the message you want to broadcast (text, photo, video, document, etc.):")

@router.callback_query(F.data == 'menu:broadcast')
async def broadcast_menu(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BroadcastStates.composing_message)
    await callback.message.edit_text("Please send the message you want to broadcast:")
    await callback.answer()

@router.callback_query(F.data.startswith('broadcast:chat:'))
async def broadcast_chat_start(callback: CallbackQuery, state: FSMContext):
    chat_id = int(callback.data.split(':')[2])
    await state.update_data(target_chat_id=chat_id)
    await state.set_state(BroadcastStates.composing_message)
    await callback.message.edit_text("Please send the message you want to broadcast to this chat's users:")
    await callback.answer()

@router.message(BroadcastStates.composing_message)
async def receive_broadcast_message(message: Message, state: FSMContext, chat_repo):
    # Store message details
    msg_data = {
        'message_id': message.message_id,
        'from_chat_id': message.chat.id
    }
    await state.update_data(msg_data=msg_data)
    
    data = await state.get_data()
    chat_id = data.get('target_chat_id')
    
    user_id = message.from_user.id
    chats = await chat_repo.get_by_admin(user_id)
    
    await state.set_state(BroadcastStates.selecting_target)
    await message.answer(
        "Message received. Please select the target audience:",
        reply_markup=broadcast_target_keyboard(chat_id, chats)
    )

@router.callback_query(BroadcastStates.selecting_target, F.data.startswith('broadcast:target:'))
async def select_broadcast_target(callback: CallbackQuery, state: FSMContext):
    target = callback.data.split(':')[2]
    target_id = None
    if target == 'chat':
        target_id = int(callback.data.split(':')[3])
    
    await state.update_data(target=target, target_id=target_id)
    await state.set_state(BroadcastStates.confirming)
    
    job_id = str(uuid.uuid4())
    await state.update_data(job_id=job_id)
    
    # Estimate recipients (placeholder)
    estimate = 100
    
    text = (
        f"📊 <b>Broadcast Summary</b>\n\n"
        f"Target: {'Specific Channel' if target == 'chat' else 'All Channels'}\n"
        f"Estimated recipients: ~{estimate}\n\n"
        "Are you ready to start?"
    )
    await callback.message.edit_text(text, reply_markup=broadcast_confirm_keyboard(job_id))

@router.callback_query(BroadcastStates.confirming, F.data.startswith('broadcast:confirm:'))
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext, broadcast_repo):
    data = await state.get_data()
    job_id = data['job_id']
    target = data.get('target')
    target_id = data.get('target_id')
    msg_data = data.get('msg_data')
    
    # Create job in db
    await broadcast_repo.create_job({
        'job_id': job_id,
        'user_id': callback.from_user.id,
        'target': target,
        'target_id': target_id,
        'msg_data': msg_data,
        'status': 'running',
        'progress': 0,
        'total': 100
    })
    
    await state.clear()
    
    text = "🚀 Broadcast started!\n\nYou can control it below:"
    await callback.message.edit_text(text, reply_markup=broadcast_control_keyboard(job_id, "running"))

@router.callback_query(F.data == 'broadcast:cancel_flow')
async def cancel_broadcast_flow(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Broadcast cancelled.")
    await callback.answer()

# Controls
@router.callback_query(F.data.startswith('broadcast:pause:'))
async def pause_via_button(callback: CallbackQuery, broadcast_repo):
    job_id = callback.data.split(':')[2]
    await broadcast_repo.update_job_status(job_id, 'paused')
    await callback.message.edit_reply_markup(reply_markup=broadcast_control_keyboard(job_id, 'paused'))

@router.callback_query(F.data.startswith('broadcast:resume:'))
async def resume_via_button(callback: CallbackQuery, broadcast_repo):
    job_id = callback.data.split(':')[2]
    await broadcast_repo.update_job_status(job_id, 'running')
    await callback.message.edit_reply_markup(reply_markup=broadcast_control_keyboard(job_id, 'running'))

@router.callback_query(F.data.startswith('broadcast:cancel:'))
async def cancel_via_button(callback: CallbackQuery, broadcast_repo):
    job_id = callback.data.split(':')[2]
    await broadcast_repo.update_job_status(job_id, 'cancelled')
    await callback.message.edit_text("Broadcast cancelled.")

@router.callback_query(F.data.startswith('broadcast:refresh_status:'))
async def refresh_broadcast_status(callback: CallbackQuery, broadcast_repo):
    job_id = callback.data.split(':')[2]
    job = await broadcast_repo.get_job(job_id)
    if not job:
        return await callback.answer("Job not found.")
        
    status = job.get('status', 'unknown')
    progress = job.get('progress', 0)
    total = job.get('total', 1)
    
    text = (
        f"📊 <b>Broadcast Status</b>\n\n"
        f"Status: {status}\n"
        f"Progress: {progress} / {total}\n"
    )
    
    if status in ['running', 'paused']:
        await callback.message.edit_text(text, reply_markup=broadcast_control_keyboard(job_id, status))
    else:
        await callback.message.edit_text(text)
    await callback.answer("Refreshed!")
