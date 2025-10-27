# The Python Template

This template provides a basic structure for creating a Python-based Mango repo. It uses the system python. If you would like to install custom dependencies or make it a full-fletched python project, consider using the `uv` template instead.

## Repo Structure

When you create a Mango repo using this template, the following folder structure will be created:

```
[project-root]
└── .mango
    ├── .instructions
    └── .on-add
```

- `on-add`: Echos the python shebang line (`#!/usr/bin/env python3`) when a new script is added to the repo.
- `.instructions`: Empty. In place to make `.mango` a valid mango folder.
