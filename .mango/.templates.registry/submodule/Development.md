# Mango Submodule Development Guide

This guide provides comprehensive information for developing Mango submodules, which are reusable components that can be integrated into Mango projects.

## Overview

A Mango submodule is a Mango repository nested inside another Mango repository's `.mango/.submodules/` folder. Submodules are designed to be:

1. Externally maintained - Users are discouraged from modifying them directly
2. Easily version managed - They must be git repositories for updating and sharing

## Creating a Submodule

To create a new submodule, use the following command:

```bash
mango @init --template submodule
```

## Submodule Basics

### Submodule Structure

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

This is the basic structure of a Mango submodule. When your submodule is installed, this directory will be copied into the `.mango/.submodules/` folder of the target project, and the `.on-install` script will be executed (if present).

- `.mango/.instructions`: Makes the directory a valid Mango folder (can be empty)
- `.mango/.on-install`: Script that runs when the submodule is installed
- `.gitignore`: Git ignore file for the submodule
- `README.md`: Documentation for the submodule
- `Development.md`: Detailed development guide, remove if not needed

### The .on-install Hook

The `.on-install` hook is executed when the submodule is installed. It receives the following environment variables:

- `MANGO_REPO_PATH`: Path to the directory containing .mango
- `MANGO_SUBMODULE_NAME`: Name of the submodule being installed
- `MANGO_SUBMODULE_PATH`: Full path to the submodule being installed to
- `MANGO`: Set to indicate that the script is being run by mango

### Working with Mango Commands

Working with submodules is the same as working with regular Mango repos. You are free to utilize mango commands you registered, including builtin commands like `@list` or `@add`. To add a script, run:

```bash
mango @add your-script-name (--bind bindings)
```

And edit it in your preferred text editor.

## Best Practices

The following best practices are recommended when developing Mango submodules:
- Do not remove the git directory. Only submodules that are git repositories can be updated and shared.
- Keep the submodule focused on a single purpose to enhance reusability.
- Keep all your code inside the `.mango/` folder. Use directories to organize your code as needed.
