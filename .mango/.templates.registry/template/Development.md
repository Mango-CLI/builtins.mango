# Mango Template Development Guide

This guide provides comprehensive information for developing Mango templates, which are special types of Mango submodules designed to scaffold new Mango repositories.

## Overview

A Mango template is a special type of Mango submodule that replaces the target repository's `.mango` folder with its own when installed. Templates are designed to be:

1. One-time setup tools - Used at repository initialization to provide starting structure
2. Easily version managed - They must be git repositories for updating and sharing
3. Self-replacing - They replace the outer `.mango` folder instead of being nested

## Creating a Template

To create a new template, use the following command:

```bash
mango @init --template template
```

## Template Basics

### Template Structure

```
[project-root]
├── .git
├── .mango
│   ├── .instructions
│   ├── .on-install
|   └── (place your scripts here)
├── .gitignore
├── Development.md
├── README.md
└── (other project files like LICENSE, etc.)
```

This is the basic structure of a Mango template. When your template is installed, its `.mango` folder will replace the target repository's `.mango` folder, and the `.on-install` script will be executed.

- `.mango/.instructions`: Makes the directory a valid Mango folder (can be empty)
- `.mango/.on-install`: Script that runs when the template is installed (handles folder replacement)
- `.gitignore`: Git ignore file for the template
- `README.md`: Documentation for the template
- `Development.md`: Detailed development guide, remove if not needed

### The .on-add Hook

When the builtin command `mango @add` is used to create a new script, the `.on-add` hook is executed (if present) to scaffold the new script. It receives the following environment variables:

- `MANGO_REPO_PATH`: path to the directory containing .mango
- `MANGO_SCRIPT_PATH`: full path to the script being created
- `MANGO_SCRIPT_NAME`: name of the script being created
- `MANGO_BINDINGS`: space-separated list of bindings added to the script

### The .on-install Hook

The `.on-install` hook is executed when the template is installed. It receives the following environment variables:

- `MANGO_REPO_PATH`: Path to the directory containing .mango
- `MANGO_SUBMODULE_NAME`: Name of the template being installed
- `MANGO_SUBMODULE_PATH`: Full path to the template being installed to
- `MANGO`: Set to indicate that the script is being run by mango

A typical `.on-install` script should replace the target's `.mango` folder with the template's `.mango` folder:

```bash
#!/bin/bash

source_path=$(dirname "$0")
target_path="${MANGO_REPO_PATH}/.mango"
tmp_name=$(echo "$source_path" | md5sum | cut -d' ' -f1)

# Replace target with source
rm -rf "/tmp/$tmp_name" && mv -f "$source_path" "/tmp/$tmp_name"
rm -rf "$target_path" && mv -f "/tmp/$tmp_name" "$target_path"

# Additional setup (git init, config files, etc.)
git init
touch .gitignore
```

### Working with Mango Commands

Working with templates is the same as working with regular Mango repos. You are free to utilize mango commands you registered, including builtin commands like `@list` or `@add`. To add a script, run:

```bash
mango @add your-script-name (--bind bindings)
```

And edit it in your preferred text editor.

## Best Practices

The following best practices are recommended when developing Mango templates:
- Do not remove the git directory. Only templates that are git repositories can be updated and shared.
- Keep all your code inside the `.mango/` folder. Use directories to organize your code as needed.
- Include comprehensive setup in the `.on-install` script (git init, configuration files, initial structure).
- Provide clear documentation in README.md about what the template creates and how to use it.
