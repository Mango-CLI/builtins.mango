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