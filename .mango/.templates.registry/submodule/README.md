# The Submodule Template

This directory contains a template for creating Mango submodules. Submodules are reusable components that can be integrated into Mango projects to provide specific functionality or features.

## Repo Structure

When you create a Mango repo using this template, the following folder structure will be created:

```
[project-root]
├── .git
├── .mango
│   ├── .instructions
│   └── .on-install
├── .gitignore
├── Development.md
└── README.md
```

- `.on-install`: Sets up git in the directory and initializes the submodule.
- `.instructions`: Empty. In place to make `.mango` a valid mango folder.
- `.gitignore`: Empty gitignore file.
- `Development.md`: Development guide for building mango submodules.
- `README.md`: Sample README file with the submodule name.
