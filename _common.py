import os
import shutil

import _cprint  # noqa: F401
from _cprint import print
from dataclasses import dataclass
from typing import Callable


#: Common Mango Structures

@dataclass
class ScriptInfo:
    virtual_submodule_path: list[str]
    within_submodule_path: str  # relative path to script from the last submodule
    source: bool
    bindings: list[str]
    
    def relativeOSPath(self) -> str:
        """get the relative OS path of the script to the base mango module.

        Return: the relative OS path of the script to the base mango module.
        """

        submodule_os_path = virtualToRelativePath(":".join(self.virtual_submodule_path))
        return os.path.join(submodule_os_path, self.within_submodule_path)
    
    def absoluteOSPath(self, base_module_path: str) -> str:
        """get the absolute OS path of the script in the mango repo.

        Keyword arguments:
        - base_module_path -- the path to the base mango module

        Return: the absolute OS path of the script in the mango repo
        """

        return os.path.join(base_module_path, self.relativeOSPath())
    
    def isBoundTo(self, binding: str) -> bool:
        """check whether the script is bound to a command.

        Keyword arguments:
        - binding -- the binding to check

        Return: bool for whether the script is bound to the binding
        """

        return binding in self.bindings


#: Common Utility Functions for Mango

def isMangoRepo(path_str: str) -> bool:
    """check whether a directory is a mango repo.

    Keyword arguments:
    - path_str -- the string of the directory to check

    Return: bool for whether the directory is a mango repo
    """

    return os.path.exists(os.path.join(path_str, ".mango"))

def isMangoModule(path_str: str) -> bool:
    """check whether a directory is a mango module.

    Keyword arguments:
    - path_str -- the string of the directory to check

    Return: bool for whether the directory is a mango module
    """

    return os.path.exists(os.path.join(path_str, ".instructions"))

def closestMangoRepo(starting_dir: str = os.getcwd()) -> str:
    """find the first mango repo up the directory tree.

    raises a FileNotFoundError if none is found.

    Return: string for the path of the closest mango repo
    """

    cur_exec_path_str = starting_dir
    while cur_exec_path_str != "/":
        if isMangoRepo(cur_exec_path_str):
            return cur_exec_path_str
        cur_exec_path_str = os.path.dirname(cur_exec_path_str)
    raise FileNotFoundError("mango repo not found")

def repoToBaseModulePath(repo_path: str) -> str:
    """convert a mango repo path to its base module path.

    raises a ValueError if the path is not a mango repo.

    Keyword arguments:
    - repo_path -- the path to the mango repo

    Return: the base module path of the mango repo
    """

    abs_repo_path = os.path.abspath(repo_path)
    if not isMangoRepo(abs_repo_path):
        raise ValueError(f"{repo_path} is not a mango repo")
    return os.path.join(abs_repo_path, ".mango")

def virtualToRelativePath(virtual_submodule_path: str) -> str:
    """convert a mango submodule path to an OS path.

    Keyword arguments:
    - virtual_path -- the virtual path to convert

    Return: the OS path of the mango submodule path
    """

    segments = virtual_submodule_path.split(":")
    ret = "."
    for segment in segments:
        ret = os.path.join(ret, '.submodules', segment)
    return ret

def getBindingsForLine(line: str) -> list[str]:
    """get the bindings from a line in the .instructions file.

    Keyword arguments:
    - line -- the line to extract bindings from

    Return: a list of bindings in the line
    """

    if ":" not in line:
        return []
    return line.split(":")[1].strip().split()

def getRegisteredScripts(mango_module_path: str, starting_submodule: list[str] = []) -> list[ScriptInfo]:
    """get a list of registered scripts in the mango repo.

    Keyword arguments:
    - mango_module_path -- the path to the mango module

    Return: a list of ScriptInfo objects representing the registered scripts
    """

    instructions_path = os.path.join(mango_module_path, ".instructions")
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
                submodule_registry = getRegisteredScripts(
                    os.path.join(
                        mango_module_path,
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

def existScript(mango_module_path: str, script_name: str) -> bool:
    """determine whether a script exists in the mango repo

    Keyword arguments:
    - mango_module_path -- the path to the mango module
    - script_name -- the name of the script
    """

    return os.path.exists(os.path.join(mango_module_path, ".mango", script_name))

def existBinding(mango_module_path: str, command_name: str) -> bool:
    """determine whether a command binding exists in the mango repo

    Keyword arguments:
    - mango_module_path -- the path to the mango module
    - command_name -- the name of the command
    """

    registered_scripts = getRegisteredScripts(mango_module_path)
    for script in registered_scripts:
        if script.isBoundTo(command_name):
            return True
    return False


#: Instructions Handlers

def enactInstructionsList(func: Callable) -> Callable:
    """enact a function on a .instruction file."""

    def wrapper(*args, **kwargs):
        instructions_path = os.path.join(
            kwargs['mango_module_path'],
            ".instructions",
        )
        with open(instructions_path, "r") as instructions_file:
            lines = instructions_file.readlines()
        lines = func(*args, **kwargs, lines=lines)
        with open(instructions_path, "w") as instructions_file:
            instructions_file.writelines(lines)

    return wrapper

@enactInstructionsList
def setSourcePolicy(mango_module_path: str, script_name: str, use_source: bool, lines: list[str] | None = None):
    """set the source policy for a single script.

    Updates the change in the .instructions file.

    Keyword arguments:
    - mango_module_path -- the path to the mango repo
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
def bindToItem(mango_module_path: str, submodule: str | None, item: str, bindings: list, lines: list[str] | None = None):
    """bind a list of commands to a script-like
    
    Keyword arguments:
    - mango_module_path -- the path to the mango repo
    - script_like -- the name of the script or submodule binding to bind to
    - bindings -- the names of the commands to bind
    - submodule -- the submodule to bind from (if any)
    """
    
    if lines is None:
        return []

    submodule_prefix = "" if submodule is None else f"[{submodule}] "
    line = f"{submodule_prefix}{item}: {' '.join(bindings)}\n"
    lines = [line] + lines
    return lines

@enactInstructionsList
def exportSubmoduleBindings(mango_module_path: str, submodule: str, lines: list[str] | None = None):
    """export bindings from a submodule.

    Keyword arguments:
    - mango_module_path -- the path to the mango repo
    - submodule -- the name of the submodule to export from
    - bindings -- the names of the commands to export
    """

    if lines is None:
        return []

    submodule_prefix = f"[{submodule}] "
    line = f"{submodule_prefix} *\n"
    lines = [line] + lines
    return lines


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
