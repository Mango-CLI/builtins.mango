import sys
import builtins

# ANSI color codes
COLORS = {
    "red": "[91m",
    "green": "[92m",
    "yellow": "[93m",
    "blue": "[94m",
    "magenta": "[95m",
    "cyan": "[96m",
    "white": "[97m"
}

# ANSI style codes
STYLES = {
    "bold": "[1m",
    "underlined": "[4m",
}

# Reset flag
RESET = "[0m"

original_print = builtins.print

def print(*args, color=None, bold=False, underlined=False, **kwargs):
    """
    Custom print function that supports colored output.

    Usage:
        print("Hello", color="red")
        print("Success!", color="green")

    Args:
        color (str, optional): The color name (red, green, yellow, etc.)
    """
    flags = ""
    
    if color in COLORS:
        flags += COLORS[color]
    if bold:
        flags += STYLES["bold"]
    if underlined:
        flags += STYLES["underlined"]
    
    sys.stdout.write(flags)
    original_print(*args, **kwargs)
    sys.stdout.write(RESET)
    sys.stdout.flush()

# Required to override print globally
builtins.print = print

def remove_ansi(string: str) -> str:
    """
    Remove all ANSI codes from a string.
    """
    import re
    ansi_escape = re.compile(r'''
        \x1B  # ESC
        (?:   # 7-bit C1 Fe (except CSI)
            [@-Z\\-_]
        |     # or [ for CSI, followed by a control sequence
            \[
            [0-?]*  # Parameter bytes
            [ -/]*  # Intermediate bytes
            [@-~]   # Final byte
        )
    ''', re.VERBOSE)
    return ansi_escape.sub('', string)

def enact_ansi(string: str) -> str:
    return string.encode('latin-1').decode('unicode_escape')