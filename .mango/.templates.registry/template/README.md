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
├── README.md
└── .gitignore
```

- `.on-install`: Sets up git in the directory and creates a new `.on-install` hook that handles the self-deletion behavior by replacing the host mango folder with the inner `.mango/` folder.
- `.instructions`: Empty. In place to make `.mango` a valid mango folder.
- `README.md`: Sample README file with the template name.
- `.gitignore`: Empty gitignore file.
