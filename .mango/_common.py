import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Callable, Literal, Optional

import _cprint  # noqa: F401
from _cprint import print
from _tui import uiTypeSelect

#: Custom Exception Hierarchy for Mango Operations

class MangoRegistryError(Exception):
    """Base exception for all Mango registry operations."""
    pass

class ItemNotFoundError(MangoRegistryError):
    """Raised when an item (template/submodule) is not found in the registry."""
    pass

class ItemAlreadyExistsError(MangoRegistryError):
    """Raised when attempting to register an item that already exists."""
    pass

class GitOperationError(MangoRegistryError):
    """Raised when a git operation fails."""
    pass

class InvalidMangoRepoError(MangoRegistryError):
    """Raised when a directory is not a valid Mango repository."""
    pass


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

@dataclass
class SubmoduleSourceInfo:
    """Information about a submodule or template source.
    
    This class handles both templates and submodules with a unified interface.
    """
    name: str
    git: str
    mode: Literal['builtin', 'registered', 'remote']
    type: Literal['template', 'submodule'] = 'submodule'
    
    @classmethod
    def from_git_repo(cls, local_path: str, type: Literal['template', 'submodule'], rename: Optional[str] = None) -> 'SubmoduleSourceInfo':
        """Create a SubmoduleSourceInfo from a local git repository path.
        
        Keyword arguments:
        - local_path -- the local path to the git repository
        
        Return: a SubmoduleSourceInfo object representing the git repository
        """
        
        name = rename or os.path.basename(local_path)
        import re
        if not re.match(r'^[\w\-.]+$', name):
            raise ValueError(f"Invalid submodule name '{name}'. Must contain only alphanumeric characters, dashes, underscores, or periods.")
        git_url = f"file://{os.path.abspath(local_path)}"
        return cls(name=name, git=git_url, mode='registered', type=type)

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

    raises an InvalidMangoRepoError if none is found.

    Return: string for the path of the closest mango repository
    """

    cur_exec_path_str = starting_dir
    while cur_exec_path_str != "/":
        if isMangoRepo(cur_exec_path_str):
            return cur_exec_path_str
        cur_exec_path_str = os.path.dirname(cur_exec_path_str)
    raise InvalidMangoRepoError("mango repo not found")

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

    Args:
        repo_path: The path to the mango repository
        
    Raises:
        MangoRegistryError: If the directory is already a mango repository or creation fails
    """
    
    from _cprint import print
    
    # Convert to absolute path
    repo_path = os.path.abspath(repo_path)
    
    # Check if the directory exists
    if not os.path.exists(repo_path):
        os.makedirs(repo_path, exist_ok=True)
    
    # Check if it's already a mango repository
    if isMangoRepo(repo_path):
        raise MangoRegistryError(f"Directory {repo_path} is already a mango repository.")
    
    # Create the basic structure
    mango_dir = os.path.join(repo_path, ".mango")
    os.makedirs(mango_dir, exist_ok=True)
    try:
        # Create .instructions file
        instructions_path = os.path.join(mango_dir, ".instructions")
        with open(instructions_path, 'w'):
            pass
        print("Created .instructions file", color='gray')
    except OSError as e:
        raise MangoRegistryError(f"Failed to create mango repository structure: {e}")

def installSubmodule(repo_path: str, git_path: str, rename_to: Optional[str] = None) -> None:
    """Install a submodule from a git repository.
    
    Args:
        repo_path: The path to the Mango repository
        git_path: The git repository URL or path
        
    Raises:
        InvalidMangoRepoError: If repo_path is not a valid Mango repository
        GitOperationError: If the git clone operation fails
    """
    # Verify the repository is a valid Mango repository
    if not isMangoRepo(repo_path):
        raise InvalidMangoRepoError(f"Path '{repo_path}' is not a valid Mango repository")
    
    submodule_name = gitBasename(git_path)
    submodules_dir = os.path.join(repo_path, ".mango", ".submodules")
    os.makedirs(submodules_dir, exist_ok=True)
    
    submodule_path = os.path.join(submodules_dir, rename_to or submodule_name)
    
    try:
        # Use subprocess directly for now to avoid circular dependency
        if not git_path.startswith("http://") and not git_path.startswith("https://") and not git_path.startswith("git@"):
            # Use direct copy instead.
            local_path = git_path.removeprefix("file://").removesuffix(".git")
            copy_from = os.path.abspath(local_path)
            shutil.copytree(copy_from, submodule_path)
        else:
            subprocess.run(
                ["git", "clone", "--recurse-submodules", git_path, submodule_path],
                check=True,
                capture_output=True,
                text=True
            )
    except subprocess.CalledProcessError as e:
        raise GitOperationError(f"Failed to install submodule '{submodule_name}': {e.stderr}")
    
    executeIfExists(os.path.join(submodule_path, '.mango', '.on-install'), kwargs={
        'MANGO_REPO_PATH': repo_path,
        'SUBMODULE_NAME': rename_to or submodule_name,
        'MANGO_SUBMODULE_PATH': submodule_path
    })


#: Shared Registry Functions for Templates and Submodules

def globForSubmoduleSources(path: str) -> list[SubmoduleSourceInfo]:
    """glob for submodule sources in a path.

    Keyword arguments:
    - path -- the path to glob for submodule sources

    Return: a list of SubmoduleSourceInfo objects representing the found submodule sources
    """

    sources: list[SubmoduleSourceInfo] = []
    if not os.path.exists(path):
        return sources

    for entry in os.listdir(path):
        entry_path = os.path.join(path, entry)
        if os.path.isdir(entry_path):
            git_path = os.path.join(entry_path, ".git")
            if os.path.exists(git_path):
                sources.append(SubmoduleSourceInfo(
                    name=entry,
                    git=f"file://{os.path.abspath(entry_path)}",
                    mode="registered",
                ))
    return sources

def getUserRegistryPath(item_type: Literal['template', 'submodule']) -> str:
    """Get the appropriate registry path for the given item type.
    
    The repository path points to the user registry, where users are free to add, audit and remove.
    
    Args:
        item_type: The type of item ('template' or 'submodule')
        
    Returns:
        The path to the appropriate registry directory
        
    Raises:
        ValueError: If item_type is not 'template' or 'submodule'
    """
    home_mango = os.path.join(homeFolder(), ".mango")
    
    if item_type == 'template':
        return os.path.join(home_mango, ".templates.registry")
    elif item_type == 'submodule':
        return os.path.join(home_mango, ".submodules.registry")
    else:
        raise ValueError(f"Invalid item_type: {item_type}. Must be 'template' or 'submodule'.")

def registerSubmodule(source_info: SubmoduleSourceInfo, item_name: str) -> str:
    """Register a template or submodule in the appropriate registry.
    
    Args:
        source_info: Information about the item to register
        item_name: The name to register the item under
        
    Returns:
        The path to the registered item
        
    Raises:
        ItemAlreadyExistsError: If the item already exists in the registry
        GitOperationError: If the git clone operation fails
    """
    registry_path = getUserRegistryPath(source_info.type)
    item_path = os.path.join(registry_path, item_name)
    
    # Check if item already exists
    if os.path.exists(item_path):
        raise ItemAlreadyExistsError(f"{source_info.type} '{item_name}' already exists in registry {registry_path}")

    # Create registry directory if it doesn't exist
    os.makedirs(registry_path, exist_ok=True)
    
    # Clone the repository
    try:
        gitCloneBare(source_info.git, item_path)
    except GitOperationError as e:
        raise GitOperationError(f"Failed to register {source_info.type} '{item_name}': {str(e)}")
    
    return item_path

def unregisterSubmodule(item_name: str, item_type: Literal['template', 'submodule']) -> None:
    """Unregister a template or submodule from the appropriate registry.
    
    Args:
        item_name: The name of the item to unregister
        item_type: The type of item ('template' or 'submodule')
        
    Raises:
        ItemNotFoundError: If the item is not found in the registry
    """
    registry_path = getUserRegistryPath(item_type)
    item_path = os.path.join(registry_path, item_name)
    
    # Check if item exists
    if not os.path.exists(item_path):
        raise ItemNotFoundError(f"{item_type} '{item_name}' not found in registry {registry_path}")
    
    # Remove the item directory
    try:
        removeFolderRecursively(item_path)
    except Exception as e:
        raise MangoRegistryError(f"Failed to unregister {item_type} '{item_name}': {str(e)}")

def listRegisteredSubmodules(path: str) -> list[SubmoduleSourceInfo]:
    """List all registered submodules in the given path.
    
    Args:
        path: The path to the directory to search for registered submodules
        
    Returns:
        A list of item names
        
    Raises:
        ValueError: If item_type is not 'template' or 'submodule'
    """
    registered_items = []
    if not os.path.exists(path):
        return registered_items
   
    for entry in os.listdir(path):
        entry_path = os.path.join(path, entry)
        git_path = os.path.join(entry_path, "config")
        if os.path.isdir(entry_path) and os.path.exists(git_path):
            registered_items.append(SubmoduleSourceInfo(
                name=entry,
                git=f"file://{os.path.abspath(entry_path)}",
                mode="registered",
            ))
    return registered_items

def gitPathFromSubmodule(submodule_like: str, registries: list[str]) -> str:
    """get the git path for a submodule-like item.

    Keyword arguments:
    - submodule_like -- the submodule-like item to get the git path for

    Return: the git path for the submodule-like item
    """

    # Direct git URL or file path
    if submodule_like.startswith("file://") or submodule_like.startswith("http://") or submodule_like.startswith("https://") or submodule_like.startswith("git@"):
        return submodule_like

    import re
    if not re.match(r'^[\w\-.]+$', submodule_like):
        raise ItemNotFoundError(f"Invalid submodule-like item '{submodule_like}'")

    # Search in registries
    for registry in registries:
        candidate_path = os.path.join(registry, submodule_like)
        git_config_path = os.path.join(candidate_path, "config")
        if os.path.exists(git_config_path):
            return f"file://{os.path.abspath(candidate_path)}"
    
    raise ItemNotFoundError(f"Submodule item '{submodule_like}' not found in registries")

#: Unified Git Operations Interface

def gitCloneBare(url: str, dest_path: str) -> None:
    """Clone a git repository with bare configuration for registry operations.
    
    Args:
        url: The git repository URL
        dest_path: The destination path for the cloned repository
        
    Raises:
        GitOperationError: If the git clone operation fails
    """
    try:
        subprocess.run(
            ["git", "clone", "--bare", url, dest_path],
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        raise GitOperationError(f"Failed to clone repository '{url}': {e.stderr}")

def gitCloneRegular(url: str, dest_path: str) -> None:
    """Clone a git repository with regular configuration for local installation.
    
    Args:
        url: The git repository URL
        dest_path: The destination path for the cloned repository
        
    Raises:
        GitOperationError: If the git clone operation fails
    """
    try:
        subprocess.run(
            ["git", "clone", "--recurse-submodules", url, dest_path],
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        raise GitOperationError(f"Failed to clone repository '{url}': {e.stderr}")

def gitPull(repo_path: str) -> None:
    """Update a repository by pulling the latest changes.
    
    Args:
        repo_path: The path to the repository to update
        
    Raises:
        GitOperationError: If the git pull operation fails
    """
    try:
        process = subprocess.Popen(
            ["git", "pull"],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        if process.stdout is not None:
            for line in process.stdout:
                print(line, end='')

        process.wait()

    except subprocess.CalledProcessError as e:
        raise GitOperationError(f"Failed to pull updates in '{repo_path}': {e.stderr}")

def handleGitError(result: subprocess.CompletedProcess) -> None:
    """Centralized error handling for git operations.
    
    Args:
        result: The result of a subprocess git command
        
    Raises:
        GitOperationError: If the git operation failed
    """
    if result.returncode != 0:
        error_msg = result.stderr.strip() if result.stderr else "Unknown git error"
        raise GitOperationError(f"Git operation failed: {error_msg}")


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
def removeAllInstructionsFromSubmodule(
    mango_repo_path: str,
    submodule: str,
    lines: list[str] | None = None,
) -> list[str]:
    """remove all bindings from a submodule.

    Keyword arguments:
    - mango_repo_path -- the path to the mango repository
    - submodule -- the name of the submodule to remove bindings from
    """

    if lines is None:
        return []

    updated_lines: list[str] = []
    submodule_prefix = f"[{submodule}]"
    for raw_line in lines:
        if raw_line.strip().startswith(submodule_prefix):
            continue
        updated_lines.append(raw_line)

    return updated_lines

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

def executeIfExists(executable_path: str, kwargs: dict, throw: bool = False) -> None:
    """execute a command if it exists in the path

    Keyword arguments:
    - executable_path -- the path to the script to execute
    - *args -- the arguments to pass to the command
    """

    if os.path.exists(executable_path):
        # Execute the command with kwargs captured as environment variables
        env = os.environ.copy()
        for key, value in kwargs.items():
            env[key] = value
        subprocess.run([executable_path], env=env)
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

    Args:
        folder_path: The path to the folder to remove
        
    Raises:
        MangoRegistryError: If the removal operation fails

    This implementation is suggested by Nick Stinemates and Mark Amery on
    StackOverflow. See link: https://stackoverflow.com/q/185936
    """

    if not os.path.exists(folder_path):
        raise MangoRegistryError(f"Folder '{folder_path}' does not exist")
        
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"Remove failed: {e}", color="white")
            raise MangoRegistryError(f"Failed to remove '{file_path}': {str(e)}")
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

def gitBasename(git: str) -> str:
    import re
    git = git.rstrip('/')
    git = re.sub(r'\.git$', '', git)
    return os.path.basename(git)