import os
import shutil

import _cprint  # noqa: F401
from _cprint import print
from dataclasses import dataclass
from typing import Callable

from _tui import uiTypeSelect


#: Common Mango Structures

@dataclass
class ScriptInfo:
    virtual_submodule_path: list[str]
    within_submodule_path: str  # relative path to script from the last submodule
    source: bool
    bindings: list[str]
    
    def relativeOSPath(self) -> str:
        """get the relative OS path of the script to the active mango repository.

        Return: the relative OS path of the script to the active mango repository.
        """

        submodule_os_path = mapSubmodulePath(":".join(self.virtual_submodule_path), base_path=".")
        return os.path.join(submodule_os_path, self.within_submodule_path)
    
    def absoluteOSPath(self, base_mango_repo: str) -> str:
        """get the absolute OS path of the script in the mango repository.

        Keyword arguments:
        - base_module_path -- the path to the active mango repository

        Return: the absolute OS path of the script in the mango repository
        """

        return os.path.abspath(os.path.join(base_mango_repo, self.relativeOSPath()))
    
    def name(self) -> str:
        """get the name of the script.

        Return: the name of the script
        """

        return os.path.basename(self.within_submodule_path)
    
    def isBoundTo(self, binding: str) -> bool:
        """check whether the script is bound to a command.

        Keyword arguments:
        - binding -- the binding to check

        Return: bool for whether the script is bound to the binding
        """

        return binding in self.bindings


#: Common Utility Functions for Mango

def isMangoRepo(path_str: str) -> bool:
    """check whether a directory is a mango repository.

    Keyword arguments:
    - path_str -- the string of the directory to check

    Return: bool for whether the directory is a mango repository
    """

    return os.path.exists(os.path.join(path_str, ".mango"))

def closestMangoRepo(starting_dir: str = os.getcwd()) -> str:
    """find the first mango repository up the directory tree.

    raises a FileNotFoundError if none is found.

    Return: string for the path of the closest mango repository
    """

    cur_exec_path_str = starting_dir
    while cur_exec_path_str != "/":
        if isMangoRepo(cur_exec_path_str):
            return cur_exec_path_str
        cur_exec_path_str = os.path.dirname(cur_exec_path_str)
    raise FileNotFoundError("mango repo not found")

def mapSubmodulePath(submodule_virtual_path: str , base_path: str) -> str:
    """maps a submodule's mango folder path to its real os path
    
    Keyword arguments:
    - submodule_virtual_path -- the submodule path to map
    - base_path -- base directory used to resolve the submodule path
    Return: the real os path of the submodule, relative to the base path
    """
    
    path = base_path
    for submodule in submodule_virtual_path.split(':'):
        path = os.path.join(path, ".mango", ".submodules", submodule)
    return path

def getBindingsForLine(line: str) -> list[str]:
    """get the bindings from a line in the .instructions file.

    Keyword arguments:
    - line -- the line to extract bindings from

    Return: a list of bindings in the line
    """

    if ":" not in line:
        return []
    return line.split(":")[1].strip().split()

def parseInstructionEntry(line: str) -> tuple[str, bool, list[str]] | None:
    """parse a top-level .instructions entry.

    Supports inline comments and ignores submodule entries.
    Returns a tuple of (script_name, is_source_entry, bindings) when the line
    represents a top-level script entry. Otherwise returns None.
    """

    stripped_line = line.strip()
    if stripped_line == "" or stripped_line.startswith("#"):
        return None

    content = stripped_line.split("#", 1)[0].strip()
    if content == "" or content.startswith("[") or ":" not in content:
        return None

    prefix, bindings_part = content.split(":", 1)
    prefix = prefix.strip()
    is_source_entry = prefix.startswith("*")
    script_name = prefix[1:] if is_source_entry else prefix
    script_name = script_name.strip()
    if script_name == "":
        return None

    bindings = bindings_part.strip().split()
    return script_name, is_source_entry, bindings

def getRegisteredItems(mango_repo_path: str, starting_submodule: list[str] = []) -> list[ScriptInfo]:
    """get a list of registered scripts in the mango repository.

    Keyword arguments:
    - mango_repo_path -- the path to the mango repository

    Return: a list of ScriptInfo objects representing the registered scripts
    """

    instructions_path = os.path.join(mango_repo_path, ".mango", ".instructions")
    scripts = []
    with open(instructions_path, "r") as instructions_file:
        for line in instructions_file:
            line = line.strip()
            if line.startswith('#') or line == "":
                continue
            
            if line.startswith("["):
                if "]" not in line:
                    continue
                submodule_name = line[1: line.index("]")]
                remaining = line[line.index("]") + 1 :].strip()
                submodule_registry = getRegisteredItems(
                    os.path.join(
                        mango_repo_path,
                        ".mango",
                        ".submodules",
                        submodule_name,
                    ),
                    starting_submodule=starting_submodule + [submodule_name],
                )
                if remaining == "*":
                    scripts += submodule_registry
                else:
                    for script in submodule_registry:
                        if script.isBoundTo(remaining):
                            scripts.append(ScriptInfo(script.virtual_submodule_path, script.within_submodule_path, script.source, [remaining]))
                continue
            
            if line.startswith("*"):
                script_path = line.split(":")[0][1:]
                bindings = line.split(":")[1].strip().split()
                source_policy = True
            else:
                script_path = line.split(":")[0]
                bindings = line.split(":")[1].strip().split()
                source_policy = False
            scripts.append(ScriptInfo(
                virtual_submodule_path=starting_submodule,
                within_submodule_path=script_path,
                source=source_policy,
                bindings=bindings,
            ))
    return scripts

def getExportedSubmodules(mango_repo_path: str) -> list[str]:
    """get a list of exported submodules in the mango repository.

    Keyword arguments:
    - mango_repo_path -- the path to the mango repository

    Return: a list of submodule names representing the exported submodules
    """

    instructions_path = os.path.join(mango_repo_path, ".mango", ".instructions")
    exported_submodules = []
    with open(instructions_path, "r") as instructions_file:
        for line in instructions_file:
            line = line.strip()
            if line.startswith('[') and line.endswith('*'):
                submodule_name = line[1: line.index("]")]
                exported_submodules.append(submodule_name)
    return exported_submodules

def existScript(mango_repo_path: str, script_name: str) -> bool:
    """determine whether a script exists in the mango repository

    Keyword arguments:
    - mango_repo_path -- the path to the mango repository
    - script_name -- the name of the script
    """

    return os.path.exists(os.path.join(mango_repo_path, ".mango", script_name))

def existBinding(mango_repo_path: str, command_name: str) -> bool:
    """determine whether a command binding exists in the mango repository

    Keyword arguments:
    - mango_repo_path -- the path to the mango repository
    - command_name -- the name of the command
    """

    registered_scripts = getRegisteredItems(mango_repo_path)
    for script in registered_scripts:
        if script.isBoundTo(command_name):
            return True
    return False

def existSubmodule(mango_repo_path: str, submodule_name: str) -> bool:
    """determine whether a submodule exists in the mango repository

    Keyword arguments:
    - mango_repo_path -- the path to the mango repository
    - submodule_name -- the name of the submodule
    """

    submodule_path = os.path.join(mango_repo_path, ".mango", ".submodules", submodule_name)
    return os.path.exists(submodule_path)

def buildEmptyMangoRepo(repo_path: str):
    """build an empty mango repository structure.

    Keyword arguments:
    - repo_path -- the path to the mango repository
    """
    
    from _cprint import fatal_error, print
    
    # Convert to absolute path
    repo_path = os.path.abspath(repo_path)
    
    # Check if the directory exists
    if not os.path.exists(repo_path):
        os.makedirs(repo_path, exist_ok=True)
    
    # Check if it's already a mango repository
    if isMangoRepo(repo_path):
        fatal_error(f"Directory {repo_path} is already a mango repository.")
    
    # Create the basic structure
    mango_dir = os.path.join(repo_path, ".mango")
    os.makedirs(mango_dir, exist_ok=True)
    try:
        # Create .instructions file
        instructions_path = os.path.join(mango_dir, ".instructions")
        with open(instructions_path, 'w') as f:
            f.write("# Mango repository instructions\n")
            f.write("# Add your script bindings here\n")
        print("Created .instructions file", color='gray')
    except OSError as e:
        fatal_error(f"Failed to create mango repository structure: {e}")

def installSubmodule(repo_path: str, git_path: str):
    """Install a submodule from a git repository."""
    submodule_name = os.path.basename(git_path)
    os.makedirs(os.path.join(repo_path, ".mango", ".submodules"), exist_ok=True)
    os.system(f"cd {os.path.join(repo_path, '.mango', '.submodules')} && git clone {git_path} --recurse-submodules")
    executeIfExists(os.path.join(repo_path, '.mango', '.submodules', submodule_name, '.on-install'), args=[repo_path])

#: Instructions Handlers

def enactInstructionsList(func: Callable) -> Callable:
    """enact a function on a .instruction file."""

    import functools
    import inspect
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Bind the provided arguments to the original function's signature
        # This allows us to find 'mango_repo_path' whether it's positional or keyword
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()

        mango_repo_path = bound_args.arguments['mango_repo_path']

        instructions_path = os.path.join(
            mango_repo_path,
            ".mango",
            ".instructions",
        )
        with open(instructions_path, "r") as instructions_file:
            lines = instructions_file.readlines()

        # Call the original function with its arguments, adding 'lines'
        lines = func(*args, **kwargs, lines=lines)

        with open(instructions_path, "w") as instructions_file:
            instructions_file.writelines(lines)

    return wrapper

def appendToTop(original: list[str], to_add: list[str]) -> list[str]:
    """append lines to the top of a list of lines, skipping empty lines and comment sections.

    Keyword arguments:
    - original -- the original list of lines
    - to_add -- the lines to add to the top

    Return: the new list of lines with the added lines at the top
    """

    insert_index = 0
    for idx, line in enumerate(original):
        stripped_line = line.strip()
        if stripped_line == "" or stripped_line.startswith("#"):
            insert_index += 1
        else:
            break
    return original[:insert_index] + to_add + original[insert_index:]

@enactInstructionsList
def setSourcePolicy(mango_repo_path: str, script_name: str, use_source: bool, lines: list[str] | None = None):
    """set the source policy for a single script.

    Updates the change in the .instructions file.

    Keyword arguments:
    - mango_repo_path -- the path to the mango repository
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

@enactInstructionsList
def bindToItem(mango_repo_path: str, submodule: str | None, item: str, bindings: list, lines: list[str] | None = None):
    """bind a list of commands to a script-like
    
    Keyword arguments:
    - mango_repo_path -- the path to the mango repository
    - script_like -- the name of the script or submodule binding to bind to
    - bindings -- the names of the commands to bind
    - submodule -- the submodule to bind from (if any)
    """
    
    if lines is None:
        return []

    submodule_prefix = "" if submodule is None else f"[{submodule}] "
    line = f"{submodule_prefix}{item}: {' '.join(bindings)}\n"
    lines = appendToTop(lines, to_add=[line])
    return lines

@enactInstructionsList
def exportSubmoduleBindings(mango_repo_path: str, submodule: str, lines: list[str] | None = None):
    """export bindings from a submodule.

    Keyword arguments:
    - mango_repo_path -- the path to the mango repository
    - submodule -- the name of the submodule to export from
    - bindings -- the names of the commands to export
    """

    if lines is None:
        return []

    submodule_prefix = f"[{submodule}]"
    line = f"{submodule_prefix} *\n"
    lines = appendToTop(lines, to_add=[line])
    return lines

@enactInstructionsList
def removeInstructionBindings(
    mango_repo_path: str,
    script_name: str,
    *,
    bindings_to_remove: set[str] | None = None,
    remove_all: bool = False,
    lines: list[str] | None = None,
) -> list[str]:
    """mutate bindings for a top-level script entry in .instructions.

    Removes bindings specified in bindings_to_remove. When remove_all is True,
    all bindings are removed (the entry is deleted). Raises ValueError if the
    target entry does not exist or a requested binding is missing unless
    remove_all is True.
    """

    if lines is None:
        return []

    target_index: int | None = None
    target_entry: tuple[str, bool, list[str]] | None = None
    for idx, raw_line in enumerate(lines):
        parsed = parseInstructionEntry(raw_line)
        if parsed is not None and parsed[0] == script_name:
            target_index = idx
            target_entry = parsed
            break

    if target_entry is None:
        if remove_all:
            return lines
        raise ValueError(f"script '{script_name}' is not registered in .instructions")

    existing_bindings = target_entry[2]
    bindings_to_remove = set() if bindings_to_remove is None else set(bindings_to_remove)
    if not remove_all:
        missing = bindings_to_remove.difference(existing_bindings)
        if missing:
            missing_list = ", ".join(sorted(missing))
            raise ValueError(
                f"bindings {missing_list} are not registered to script '{script_name}'"
            )

    updated_bindings = [] if remove_all else [b for b in existing_bindings if b not in bindings_to_remove]

    assert target_index is not None
    original_line = lines[target_index]
    line_ending = "\n" if original_line.endswith("\n") else ""

    if len(updated_bindings) == 0:
        lines.pop(target_index)
    else:
        prefix = "*" if target_entry[1] else ""
        lines[target_index] = f"{prefix}{script_name}: {' '.join(updated_bindings)}{line_ending}"

    return lines

@enactInstructionsList
def deleteInstructionEntry(
    mango_repo_path: str,
    script_name: str,
    lines: list[str] | None = None,
) -> list[str]:
    """delete a top-level .instructions entry for the provided script name."""

    if lines is None:
        return []

    updated_lines: list[str] = []
    for raw_line in lines:
        parsed = parseInstructionEntry(raw_line)
        if parsed is not None and parsed[0] == script_name:
            continue
        updated_lines.append(raw_line)

    return updated_lines


#: Broad Utility Functions

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

def confirmDestructiveAction(prompt: str, *, default_yes: bool = True) -> bool:
    """prompt the user for confirmation on destructive actions."""
    options = ["y", "n"]
    default_index = 0 if default_yes else 1
    choice = uiTypeSelect(prompt=prompt, options=options, default_id=default_index)
    return choice == 0

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

def openInEditor(editor: str, file_path: str) -> None:
    """open a file in an editor

    Keyword arguments:
    - editor -- the command to open the editor
    - file_path -- the path to the file to open
    """

    os.system(f"{editor} {file_path}")

def homeFolder() -> str:
    import getpass
    return f"/home/{getpass.getuser()}"

def globPath(paths: list[str], name: str) -> str | None:
    for path in paths:
        if os.path.exists(os.path.join(path, name)):
            return os.path.join(path, name)
    return None

def retrievePathFromEnv(var: str, default: list[str] = []):
    envResult = os.environ.get(var)
    envList = envResult.split(':') if envResult is not None else []
    return list(filter(lambda x: len(x) > 0, envList + default))