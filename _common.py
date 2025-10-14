import os
import shutil

import _print_utils  # noqa: F401
from _print_utils import print


def existMangoRepo(scan_path_str: str) -> bool:
    """check whether a directory is a mango repo.

    Keyword arguments:
    - scan_path_str -- the string of the directory to check

    Return: bool for whether the directory is a mango repo
    """

    return os.path.exists(os.path.join(scan_path_str, ".mango"))

def closestMangoRepo(starting_dir: str = os.getcwd()) -> str:
    """find the first mango repo up the directory tree.

    raises a FileNotFoundError if none is found.

    Return: string for the path of the closest mango repo
    """

    cur_exec_path_str = starting_dir
    while cur_exec_path_str != "/":
        if existMangoRepo(cur_exec_path_str):
            return cur_exec_path_str
        cur_exec_path_str = os.path.dirname(cur_exec_path_str)
    raise FileNotFoundError("mango repo not found")

def executeIfExists(executable_path: str, args, throw: bool = False) -> None:
    """execute a command if it exists in the path

    Keyword arguments:
    - executable_path -- the path to the script to execute
    - *args -- the arguments to pass to the command
    """

    if os.path.exists(executable_path):
        quoted_args = [f'"{arg}"' for arg in args]
        command = " ".join([executable_path] + quoted_args)
        os.system(command)
    elif throw:
        raise FileNotFoundError(f"{executable_path} not found")

def removeFolderRecursively(folder_path: str) -> None:
    """remove a folder and all its contents.

    Keyword arguments:
    - folder_path -- the path to the folder to remove

    This implementation is suggested by Nick Stinemates and Mark Amery on
    StackOverflow. See link: https://stackoverflow.com/q/185936
    """

    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"Remove failed: {e}", color="white")
            raise e
    os.rmdir(folder_path)

def existRegisteredScript(repo_path: str, script_name: str) -> bool:
    """determine whether a script is registered in the .instructions file.

    Keyword arguments:
    - repo_path -- the path to the mango repo
    - script_name -- the name of the script
    """

    instructions_path = os.path.join(repo_path, ".mango", ".instructions")
    with open(instructions_path, "r") as instructions_file:
        for line in instructions_file:
            if line.startswith(f"{script_name}:") or line.startswith(
                f"*{script_name}:"
            ):
                return True
    return False

def existRegisteredCommand(repo_path: str, command_name: str) -> bool:
    """determine whether a command is registered in the .instructions file.

    Keyword arguments:
    - repo_path -- the path to the mango repo
    - command_name -- the name of the command
    """

    instructions_path = os.path.join(repo_path, ".mango", ".instructions")
    with open(instructions_path, "r") as instructions_file:
        for line in instructions_file:
            line = line.strip()
            if line.startswith('#'):
                continue
            # fix: prone to error when there is a script whose name corresponds to a
            # command, but the command has not been registered
            line = line.split(":")[1].strip()
            if command_name in line.split(" "):
                return True
    return False

def existScript(repo_path: str, script_name: str) -> bool:
    """determine whether a script exists in the mango repo

    Keyword arguments:
    - repo_path -- the path to the mango repo
    - script_name -- the name of the script
    """

    return os.path.exists(os.path.join(repo_path, ".mango", script_name))

def registerNewScript(repo_path: str, script_name: str) -> None:
    """register a new script in the mango repo

    Keyword arguments:
    - repo_path -- the path to the mango repo
    - script_name -- the name of the script to register
    """

    script_path = os.path.join(repo_path, ".mango", script_name)
    with open(script_path, "a"):
        pass
    os.chmod(script_path, 0o754)

    instructions_path = os.path.join(repo_path, ".mango", ".instructions")
    with open(instructions_path, "a") as instructions_file:
        instructions_file.write(f"{script_name}:")

def bindCommandsToScript(repo_path: str, command_names: list, script_name: str) -> None:
    """bind a list of commands to a script in the mango repo.

    Keyword arguments:
    - repo_path -- the path to the mango repo
    - command_names -- the names of the commands to bind
    - script_name -- the name of the script to bind to the commands
    """

    instructions_path = os.path.join(repo_path, ".mango", ".instructions")
    lines = []
    has_appended = False
    with open(instructions_path, "r") as instructions_file:
        lines = instructions_file.readlines()

        def processLine(line: str) -> str:
            if line.startswith(f"{script_name}:") or line.startswith(
                f"*{script_name}:"
            ):
                print(f"line: {line}", color="gray")
                nonlocal has_appended
                has_appended = True
                present_commands = line.split(":")[1].strip().split(" ")
                # this edge case happens when the list is originally empty
                if present_commands == [""]:
                    present_commands = []
                print(
                    "present_commands: {present_commands} "
                    "command_names: {command_names}".format(
                        present_commands=present_commands,
                        command_names=command_names,
                    ),
                    color="gray"
                )
                new_commands = set(present_commands + command_names)
                line = f"{script_name}: {' '.join(new_commands)}\n"
            return line

        lines = [processLine(line) for line in lines]

    if not has_appended:
        lines.append(f"{script_name}: {' '.join(command_names)}\n")
    with open(instructions_path, "w") as instructions_file:
        instructions_file.writelines(lines)

def openInEditor(editor: str, file_path: str) -> None:
    """open a file in an editor

    Keyword arguments:
    - editor -- the command to open the editor
    - file_path -- the path to the file to open
    """

    os.system(f"{editor} {file_path}")

# decorator
def enactInstructionsList(func):
    """enact a function on a .instruction file."""

    def wrapper(*args, **kwargs):
        instructions_path = os.path.join(
            kwargs['repo_path'],
            ".mango",
            ".instructions",
        )
        with open(instructions_path, "r") as instructions_file:
            lines = instructions_file.readlines()
        lines = func(*args, **kwargs, lines=lines)
        with open(instructions_path, "w") as instructions_file:
            instructions_file.writelines(lines)

    return wrapper

@enactInstructionsList
def dereferenceScript(repo_path: str, script_name: str, lines=None):
    """dereference a script in the mango repo.

    Removes it completely from the .instructions file.

    Keyword arguments:
    - repo_path -- the path to the mango repo
    - lines -- the lines of the .instructions file
    - script_name -- the name of the script to dereference
    """

    if lines is None:
        return []

    prefixes = (f"{script_name}:", f"*{script_name}:")
    return [line for line in lines if not line.startswith(prefixes)]

@enactInstructionsList
def unbindScriptAll(repo_path: str, script_name: str, lines=None):
    """unbind a script from all commands in the mango repo.

    Keeps an empty entry in the .instructions file.

    Keyword arguments:
    - repo_path -- the path to the mango repo
    - script_name -- the name of the script to unbind

    The 'lines' parameter is handled by the enactInstructionsList decorator
    """

    if lines is None:
        return []

    def processLine(line: str) -> str:
        if line.startswith(f"{script_name}:"):
            return f"{script_name}:\n"
        if line.startswith(f"*{script_name}:"):
            return f"*{script_name}:\n"
        return line

    return [processLine(line) for line in lines]

@enactInstructionsList
def unbindScriptSelectively(
    repo_path: str,
    script_name: str,
    command_names: list,
    lines=None,
):
    """unbind a script from a list of commands in the mango repo.

    Keyword arguments:
    - repo_path -- the path to the mango repo
    - script_name -- the name of the script to unbind
    - command_names -- the names of the commands to unbind

    The 'lines' parameter is handled by the enactInstructionsList decorator
    """

    if lines is None:
        return []

    def processLine(line: str) -> str:
        if line.startswith(f"{script_name}:"):
            present_commands = line.split(":")[1].strip().split(" ")
            # this edge case happens when the list is originally empty
            if present_commands == [""]:
                present_commands = []
            new_commands = set(present_commands) - set(command_names)
            return f"{script_name}: {' '.join(new_commands)}\n"
        if line.startswith(f"*{script_name}:"):
            present_commands = line.split(":")[1].strip().split(" ")
            if present_commands == [""]:
                present_commands = []
            new_commands = set(present_commands) - set(command_names)
            return f"*{script_name}: {' '.join(new_commands)}\n"
        return line

    return [processLine(line) for line in lines]

@enactInstructionsList
def setSourcePolicy(repo_path: str, script_name: str, use_source: bool, lines=None):
    """set the source policy for a single script.

    Updates the change in the .instructions file.

    Keyword arguments:
    - repo_path -- the path to the mango repo
    - lines -- the lines of the .instructions file
    - script_name -- the name of the script to dereference
    - use_source -- the new source policy for the script
    """

    if lines is None:
        return []

    def processLine(line: str) -> str:
        if line.startswith(f"{script_name}:") and use_source:
            return f"*{script_name}: {line.split(':')[1]}"
        if line.startswith(f"*{script_name}:") and not use_source:
            return f"{script_name}: {line.split(':')[1]}"
        return line

    return [processLine(line) for line in lines]
