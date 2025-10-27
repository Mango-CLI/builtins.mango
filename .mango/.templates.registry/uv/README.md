# The UV Template

This template provides a basic structure for creating a Mango repo that uses Astro UV as the python runtime environment.

## Repo Structure

When you create a Mango repo using this template, the following folder structure will be created:

```
[project-root]
└── .mango
    ├── .instructions
    ├── activate
    └── (uv-generated)
```

- `activate`: This script is sourced by default and sets up the venv for the project.
- `.instructions`: Includes a single entry binding sourced script `activate` to "activate".
