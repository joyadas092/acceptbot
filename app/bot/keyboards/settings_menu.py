from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def approval_settings_keyboard(
    chat_id: int,
    auto_approval: bool,
    delay_seconds: int
) -> InlineKeyboardMarkup:
    """Approval settings keyboard."""
    builder = InlineKeyboardBuilder()
    
    toggle_text = "🟢 Auto Approval: ON" if auto_approval else "🔴 Auto Approval: OFF"
    builder.button(text=toggle_text, callback_data=f"approval:toggle:{chat_id}")
    
    # Delay options
    delays = [
        ("⚡ Immediate", 0),
        ("⏱ 1m", 60),
        ("⏱ 5m", 300),
        ("⏱ 15m", 900),
        ("⏱ 30m", 1800),
        ("⏱ 1h", 3600),
        ("⏱ 2h", 7200)
    ]
    
    for text, val in delays:
        # Mark active delay
        btn_text = f"✅ {text}" if delay_seconds == val else text
        builder.button(text=btn_text, callback_data=f"approval:delay:{chat_id}:{val}")
        
    builder.button(text="✏️ Custom", callback_data=f"approval:delay:{chat_id}:custom")
    builder.button(text="← Back", callback_data=f"chat:select:{chat_id}")
    
    builder.adjust(1, 3, 3, 2, 1)
    return builder.as_markup()

def welcome_settings_keyboard(
    chat_id: int,
    welcome_enabled: bool,
    trigger: str,
    delay_seconds: int
) -> InlineKeyboardMarkup:
    """Welcome message settings keyboard."""
    builder = InlineKeyboardBuilder()
    
    toggle_text = "🟢 Welcome: ON" if welcome_enabled else "🔴 Welcome: OFF"
    builder.button(text=toggle_text, callback_data=f"welcome:toggle:{chat_id}")
    
    # Triggers
    triggers = [
        ("📨 On Request", "on_request"),
        ("✅ On Approval", "on_approval"),
        ("⏱ After Appr. + Delay", "delayed")
    ]
    
    for text, val in triggers:
        btn_text = f"✅ {text}" if trigger == val else text
        builder.button(text=btn_text, callback_data=f"welcome:trigger:{chat_id}:{val}")
        
    builder.adjust(1, 3)
    
    if trigger == "delayed":
        delays = [
            ("⏱ 5m", 300),
            ("⏱ 15m", 900),
            ("⏱ 30m", 1800)
        ]
        delay_row = []
        for text, val in delays:
            btn_text = f"✅ {text}" if delay_seconds == val else text
            delay_row.append(builder.button(text=btn_text, callback_data=f"welcome:delay:{chat_id}:{val}"))
        
        builder.button(text="✏️ Custom", callback_data=f"welcome:delay:{chat_id}:custom")
        builder.adjust(1, 3, 4)
        
    # Actions
    builder.row(
        builder.button(text="✏️ Edit Message", callback_data=f"welcome:edit_text:{chat_id}"),
        builder.button(text="🔘 Edit Buttons", callback_data=f"welcome:edit_buttons:{chat_id}"),
        builder.button(text="👁 Preview", callback_data=f"welcome:preview:{chat_id}")
    )
    
    builder.row(builder.button(text="← Back", callback_data=f"chat:select:{chat_id}"))
    
    return builder.as_markup()
