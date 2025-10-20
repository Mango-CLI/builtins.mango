import sys
import tty
import termios
from typing import List, TypedDict, NotRequired
import _cprint

from _cprint import print

def getKey():
    """Reads a single key press and blocks until a key is pressed."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    try:
        tty.setraw(fd)  # Set terminal to raw mode (no buffering)
        key = sys.stdin.read(1)  # Read a single character
        
        if key == '\x1b':
            key += sys.stdin.read(2)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)  # Restore settings

    return key

def hideCursor(func):
    """Decorator that hides the cursor before running the function and shows it afterwards."""
    def wrapper(*args, **kwargs):
        try:
            print("[?25l", end='')  # Hide cursor
            return func(*args, **kwargs)
        finally:
            print("[?25h", end='')  # Show cursor
    return wrapper

def removeLines(n: int):
    """Removes the last n lines from the terminal."""
    for _ in range(n):
        print("[F[K", end='')


#: User Interface Utilities

class UIInputStyle(TypedDict):
    """A dictionary defining the styles for the uiInput function."""
    prompt_color: NotRequired[str]
    response_color: NotRequired[str]
    prefix: NotRequired[str]
    bold: NotRequired[bool]

def uiInput(prompt: str, style: UIInputStyle | None = None) -> str:
    """Prints a prompt and returns the user input."""
    
    default_style = {
        "prompt_color": "white",
        "response_color": "white",
        "prefix": "> ",
        "bold": True
    }
    merged_style = {**default_style, **(style or {})}

    print(merged_style["prefix"], color=merged_style["prompt_color"], bold=merged_style["bold"], end='')
    if prompt:
        print(f"({prompt}) ", color=merged_style["prompt_color"], bold=merged_style["bold"], end='')
    try:
        _cprint.original_print(_cprint.COLORS[merged_style["response_color"]], end='')
        response = input()
    finally:
        _cprint.original_print(_cprint.RESET, end='')
    return response

class UITypeSelectStyle(TypedDict):
    """A dictionary defining the styles for the uiTypeSelect function."""
    prompt_color: NotRequired[str]
    prompt_bold: NotRequired[bool]
    options_color: NotRequired[str]

def uiTypeSelect(prompt: str, options: List[str], default_id: int, style: UITypeSelectStyle | None = None) -> int:
    """Prints a prompt and allows the user to type to select an option from the list."""
    default_style = {
        "prompt_color": "white",
        "prompt_bold": True,
        "options_color": "gray"
    }
    merged_style = {**default_style, **(style or {})}

    print(prompt, color=merged_style["prompt_color"], bold=merged_style["prompt_bold"], end=' ')
    extension_str = '['
    for i, option in enumerate(options):
        if i == default_id:
            extension_str += f"{option}".upper()
        else:
            extension_str += f"{option}".lower()
        if i != len(options) - 1:
            extension_str += '/'
    extension_str += ']'
    print(extension_str, end=' ')
    response = input().strip().lower()
    if response == '':
        return default_id
    for i, option in enumerate(options):
        if response == option.lower():
            return i
    return default_id

class UISelectStyle(TypedDict):
    """A dictionary defining the styles for the uiSelect function."""
    selected_prefix: NotRequired[str]
    selected_color: NotRequired[str]
    unselected_prefix: NotRequired[str]
    unselected_color: NotRequired[str]

@hideCursor
def uiSelect(options: List[str], style: UISelectStyle | None = None):
    """
    Launches a select menu with the given options and returns the index of the selected option.

    Args:
        options: A list of strings to be displayed as options.
        style: An optional dictionary to customize the appearance.
    """
    
    default_style = {
        "selected_prefix": "> ",
        "selected_color": "white",
        "unselected_prefix": "  ",
        "unselected_color": "gray"
    }
    merged_style = {**default_style, **(style or {})}

    selected_line_number = 0
    while True:
        # first print the options
        for i, option in enumerate(options):
            if i == selected_line_number:
                print(merged_style["selected_prefix"], color=merged_style["selected_color"], end='')
                print(option, color=merged_style["selected_color"], underlined=True)
            else:
                print(merged_style["unselected_prefix"], color=merged_style["unselected_color"], end='')
                print(option, color=merged_style["unselected_color"])

        # then get the user input
        key = getKey()

        # handle the user input
        if key == '\x1b[A':
            selected_line_number = max(0, selected_line_number - 1)
        elif key == '\x1b[B':
            selected_line_number = min(len(options) - 1, selected_line_number + 1)
        elif key == '\x0d':
            return selected_line_number
        elif key == '\x03':
            print("ctrl-c")
            exit(0)
        # clear the lines above
        removeLines(len(options))
