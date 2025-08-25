import re
from pyrogram import filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode as PM

from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

# ─── ALLOWED CHARACTERS ───
MATH_PATTERN = re.compile(r"^[\d\s\+\-\*\/\%\(\)\.]+$")

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
        return eval(expr, {"__builtins__": {}}, {})
    except Exception:
        return None


@Gojo.on_message(filters.text & filters.group, group=8)
async def calc_handler(c: Gojo, m: Message):
    expr = m.text.strip()

    # Ignore commands (so /help etc won’t trigger)
    if expr.startswith("/"):
        return

    result = safe_eval(expr)
    if result is not None:
        await m.reply_text(
            f"🧮 **Calculation**\n`{expr}` = **{result}**",
            parse_mode=PM.MARKDOWN,
            reply_to_message_id=m.id
        )


__PLUGIN__ = "calc"

_DISABLE_CMDS_ = []

__alt_name__ = []

__HELP__ = """
**Calculator**
Just send a math expression in chat and I’ll solve it.

Examples:
• `2+2`
• `(10*5)/2`
• `50%5`
"""
