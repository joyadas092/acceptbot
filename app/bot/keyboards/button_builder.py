from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def button_builder_keyboard(
    chat_id: int,
    buttons: list[dict]
) -> InlineKeyboardMarkup:
    """Button builder management keyboard."""
    builder = InlineKeyboardBuilder()
    
    # Existing buttons
    for idx, btn in enumerate(buttons):
        text = btn.get('text', 'Button')
        if len(text) > 15:
            text = text[:12] + "..."
        row = btn.get('row', 1)
        builder.button(text=f"❌ {text} (Row {row})", callback_data=f"btn:delete:{chat_id}:{idx}")
    
    if buttons:
        builder.adjust(1)
        
    builder.row(
        builder.button(text="➕ Add Button", callback_data=f"btn:add:{chat_id}")
    )
    
    builder.row(
        builder.button(text="👁 Preview", callback_data=f"btn:preview:{chat_id}"),
        builder.button(text="💾 Save", callback_data=f"btn:save:{chat_id}")
    )
    
    builder.row(builder.button(text="← Back", callback_data=f"settings:welcome:{chat_id}"))
    
    return builder.as_markup()

def button_row_selector_keyboard(
    chat_id: int,
    existing_rows: list[int]
) -> InlineKeyboardMarkup:
    """Let admin choose which row to place a new button."""
    builder = InlineKeyboardBuilder()
    
    rows = sorted(list(set(existing_rows)))
    for r in rows:
        builder.button(text=f"Row {r}", callback_data=f"btn:row:{chat_id}:{r}")
        
    next_row = (max(rows) + 1) if rows else 1
    builder.button(text=f"New Row ({next_row})", callback_data=f"btn:row:{chat_id}:{next_row}")
    
    builder.adjust(2)
    builder.row(builder.button(text="❌ Cancel", callback_data=f"settings:buttons:{chat_id}"))
    
    return builder.as_markup()
