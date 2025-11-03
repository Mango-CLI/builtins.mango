# The Template Template

This directory contains a template for creating Mango templates. A template is a special type of Mango submodule that deletes itself after it has been used to scaffold a new Mango repository.

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
