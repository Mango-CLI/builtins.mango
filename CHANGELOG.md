# Changelog

## [2.0.0] - 2025-10-28

**Compatible with Mango 2.0.0 and above.**

### Changed

- Migrate `builtins.mango` to new repository.
- Migrated old single-layer structure to modern submodule-based architecture.
- Rewrote all built-in modules.

### Added

- Added builtin support for `help`, `which`, `self`, `submodule` and `template` commands.

## [2.0.1] - 2025-10-28

**Compatible with Mango 2.0.0 and above.**

### Added

- Added CHANGELOG.md file to maintain history.

### Fixed

- Fixed issue with installing submodules from local git repositories.
- Fixed `mango @template init` command not executing properly.

## [2.0.2] - 2025-11-5

### Added

- Dev guide to templates "submodule" and "template".

## [2.0.3] - 2025-12-2

### Fixed

- Issue with `mango @add` command not working with python <= 3.10 due to typing import error.