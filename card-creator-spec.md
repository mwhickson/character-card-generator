# (Silly)Tavern Character Card Creator

This specification outlines the purpose, features and other details for a Tavern/SillyTavern Charactor Card Creator application.

## Requirements

- MUST be a desktop application
- SHOULD be cross-platform
- MUST minimize build system overhead
- MUST provide an easy deploy/install target (e.g. XCOPY deploy)
- MUST support version 2 of the Character Card format
- MUST support user input for all Character Card properties
- SHOULD prioritize key Character Card properties
- SHOULD streamline the user interface to support key Character Card properties
- MUST support round-trip editing (save/load)

## Features

- simple and straightforward guided character creation via a focused application UI
- supports Character Card saves (in version 2 format) to either JSON or PNG
- supports Character Card loads (from version 1 or version 2 format) from either JSON or PNG
- displays token counts in an easy to review format throughout the character creation process
- easy to build; easy to deploy
- validates character format on load and ensures saved character files are valid
