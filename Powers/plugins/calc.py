import re
from pyrogram import filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode as PM

from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

# ─── ALLOWED CHARACTERS ───
MATH_PATTERN = re.compile(r"^[\d\s\+\-\*\/\%\(\)\.]+$")

# Pattern to detect if it's a simple number (no operators)
SIMPLE_NUMBER_PATTERN = re.compile(r"^\s*\d*\.?\d+\s*$")

def safe_eval(expr: str):
    """
    Safely evaluate a math expression.
    Allowed: +, -, *, /, %, (), numbers, decimal
    """
    try:
        # Remove spaces
        expr = expr.replace(" ", "")
        if not MATH_PATTERN.match(expr):
            return None
        # Eval in restricted namespace
        result = eval(expr, {"__builtins__": {}}, {})
        
        # Handle floating point precision issues
        if isinstance(result, float):
            # Check if the result is effectively an integer
            if result.is_integer():
                return int(result)
            # Round to reasonable precision for decimal results
            else:
                # Count decimal places in the original expression
                decimal_places = 0
                numbers = re.findall(r"\d*\.\d+", expr)
                for num in numbers:
                    places = len(num.split('.')[1])
                    decimal_places = max(decimal_places, places)
                
                # Round to maximum of 10 places or the original precision + 2
                round_to = min(max(decimal_places + 2, 2), 10)
                return round(result, round_to)
        
        return result
    except Exception:
        return None


@Gojo.on_message(filters.text & filters.group, group=8)
async def calc_handler(c: Gojo, m: Message):
    expr = m.text.strip()

    # Ignore commands (so /help etc won't trigger)
    if expr.startswith("/"):
        return
        
    # Don't respond to simple numbers without operators
    if SIMPLE_NUMBER_PATTERN.match(expr):
        return

    result = safe_eval(expr)
    if result is not None:
        await m.reply_text(
            f"🧮 **Calculation**\n`{expr}` = **{result}**",
            parse_mode=PM.MARKDOWN,
            reply_to_message_id=m.id
        )


__PLUGIN__ = "ᴄᴀʟᴄᴜʟᴀᴛᴏʀ"

_DISABLE_CMDS_ = []

__alt_name__ = []

__HELP__ = """
**ᴄᴀʟᴄᴜʟᴀᴛᴏʀ**
ᴊᴜsᴛ sᴇɴᴅ ᴀ ᴍᴀᴛʜ ᴇxᴘʀᴇssɪᴏɴ ɪɴ ᴄʜᴀᴛ ᴀɴᴅ ɪ'ʟʟ sᴏʟᴠᴇ ɪᴛ.

ᴇxᴀᴍᴘʟᴇs:
• `2+2`
• `(10*5)/2`
• `50%5`
• `0.1+0.2` (now shows 0.3 instead of 0.30000000000000004)
"""
