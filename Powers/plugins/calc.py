import re
import math
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.enums import ParseMode as PM

from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

# ─── ALLOWED CHARACTERS AND FUNCTIONS ───
MATH_PATTERN = re.compile(r"^[\d\s\+\-\*\/\%\(\)\.\,\^√π𝑒!abs|sincostanloglnsqrt]+$")

# Pattern to detect if it's a simple number (no operators)
SIMPLE_NUMBER_PATTERN = re.compile(r"^\s*\d*\.?\d+\s*$")

# Supported functions and constants
MATH_FUNCTIONS = {
    'sin': math.sin,
    'cos': math.cos,
    'tan': math.tan,
    'log': math.log10,
    'ln': math.log,
    'sqrt': math.sqrt,
    'abs': abs,
    'π': math.pi,
    'pi': math.pi,
    '𝑒': math.e,
    'e': math.e,
    '^': pow,
    '√': math.sqrt
}

def safe_eval(expr: str):
    """
    Safely evaluate a math expression with advanced functions.
    """
    try:
        # Preprocess the expression
        expr = expr.replace(" ", "").replace(",", "").lower()
        
        # Replace common math symbols
        expr = expr.replace("×", "*").replace("÷", "/").replace("**", "^")
        
        # Validate the expression
        if not MATH_PATTERN.match(expr):
            return None, "Invalid characters detected"
        
        # Replace functions and constants
        for func_name, func in MATH_FUNCTIONS.items():
            if func_name in expr:
                if func_name in ['π', 'pi', '𝑒', 'e']:
                    expr = expr.replace(func_name, str(func))
                else:
                    # Handle function calls
                    expr = re.sub(rf"{func_name}\(([^)]+)\)", 
                                 lambda m: f"{func.__name__}({m.group(1)})", expr)
        
        # Handle factorial
        if '!' in expr:
            expr = re.sub(r'(\d+)!', r'math.factorial(\1)', expr)
        
        # Handle square root with √ symbol
        expr = re.sub(r'√(\d+)', r'math.sqrt(\1)', expr)
        
        # Handle exponentiation with ^ symbol
        expr = re.sub(r'(\d+)\^(\d+)', r'pow(\1,\2)', expr)
        
        # Create safe namespace
        safe_namespace = {
            'math': math,
            'pow': pow,
            'abs': abs,
            '__builtins__': {}
        }
        
        # Evaluate the expression
        result = eval(expr, safe_namespace)
        
        # Handle floating point precision issues
        if isinstance(result, (int, float)):
            result = format_result(result, expr)
        
        return result, None
        
    except ZeroDivisionError:
        return None, "Division by zero error"
    except ValueError as e:
        return None, f"Math error: {str(e)}"
    except Exception as e:
        return None, f"Evaluation error: {str(e)}"

def format_result(result, original_expr):
    """
    Format the result with appropriate precision and formatting.
    """
    if isinstance(result, int):
        return result
    
    # Handle very large or very small numbers
    if abs(result) > 1e10 or (abs(result) < 1e-10 and result != 0):
        return f"{result:.4e}"
    
    # Handle floating point precision
    if isinstance(result, float):
        # Check if it's effectively an integer
        if result.is_integer():
            return int(result)
        
        # Count decimal places in original numbers
        decimal_numbers = re.findall(r"\d*\.\d+", original_expr)
        max_decimal_places = 0
        for num in decimal_numbers:
            decimal_part = num.split('.')[1]
            max_decimal_places = max(max_decimal_places, len(decimal_part))
        
        # Round appropriately (max 8 decimal places)
        round_to = min(max(max_decimal_places, 4), 8)
        rounded = round(result, round_to)
        
        # Remove trailing zeros
        if rounded == int(rounded):
            return int(rounded)
        return rounded
    
    return result

@Gojo.on_message(filters.text & filters.group, group=8)
async def calc_handler(c: Gojo, m: Message):
    expr = m.text.strip()

    # Ignore commands
    if expr.startswith("/"):
        return
        
    # Don't respond to simple numbers without operators
    if SIMPLE_NUMBER_PATTERN.match(expr):
        return

    result, error = safe_eval(expr)
    
    if error:
        # Don't respond with errors for every message
        return
    
    if result is not None:
        # Create help button
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📚 Calculator Help", callback_data="calc_help")]
        ])
        
        await m.reply_text(
            f"🧮 **Advanced Calculation**\n\n"
            f"**Expression:** `{expr}`\n"
            f"**Result:** `{result}`\n\n",
            parse_mode=PM.MARKDOWN,
            reply_to_message_id=m.id,
            reply_markup=keyboard
        )

@Gojo.on_callback_query(filters.regex("^calc_help$"))
async def calc_help_callback(c: Gojo, query):
    await query.answer()
    await query.message.edit_text(
        text=__HELP__,
        parse_mode=PM.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="calc_back")]
        ])
    )

@Gojo.on_callback_query(filters.regex("^calc_back$"))
async def calc_back_callback(c: Gojo, query):
    await query.answer()
    # You might want to store the original result message to restore it
    await query.message.delete()

@Gojo.on_message(command("calc"))
async def calc_command(c: Gojo, m: Message):
    """Direct calculator command"""
    if len(m.command) < 2:
        await m.reply_text("Please provide an expression to calculate!\nExample: `/calc 2+2*3`")
        return
    
    expr = " ".join(m.command[1:])
    result, error = safe_eval(expr)
    
    if error:
        await m.reply_text(f"❌ **Error:** {error}")
        return
    
    await m.reply_text(
        f"🧮 **Calculation Result**\n\n"
        f"**Expression:** `{expr}`\n"
        f"**Result:** `{result}`",
        parse_mode=PM.MARKDOWN
    )

__PLUGIN__ = "ᴀᴅᴠᴀɴᴄᴇᴅ ᴄᴀʟᴄᴜʟᴀᴛᴏʀ"

_DISABLE_CMDS_ = []

__alt_name__ = ["calculator", "calc"]

__HELP__ = """
**🧮 ADVANCED CALCULATOR**

**Basic Operations:**
• `2 + 3 * 4` - Basic arithmetic
• `(5 + 3) / 2` - Parentheses support
• `10 % 3` - Modulo operation

**Advanced Functions:**
• `sin(45)`, `cos(30)`, `tan(60)` - Trigonometric functions
• `log(100)`, `ln(10)` - Logarithmic functions
• `sqrt(16)` or `√16` - Square root
• `5!` - Factorial
• `2^8` or `2**8` - Exponentiation

**Constants:**
• `π` or `pi` - Pi (3.14159...)
• `𝑒` or `e` - Euler's number (2.71828...)

**Examples:**
• `sin(π/2)` = 1.0
• `sqrt(25) + 2^3` = 13
• `log(1000) * 2` = 6.0
• `5! / 2` = 60

**Note:** The calculator automatically handles floating point precision and supports scientific notation for very large/small numbers.

**Commands:**
• Just type math expressions in chat
• Or use `/calc <expression>` for direct calculation
"""

# Add command handler for the calc command
@Gojo.on_message(command("calculator"))
async def calculator_help(c: Gojo, m: Message):
    await m.reply_text(__HELP__, parse_mode=PM.MARKDOWN)
