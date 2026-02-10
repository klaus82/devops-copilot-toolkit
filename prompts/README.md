# Prompt Instructions

Reusable instruction files for GitHub Copilot.

## Usage

### VS Code User Prompts

Symlink or copy files to your VS Code user prompts folder:

```bash
# macOS
ln -s $(pwd)/<file>.instructions.md ~/Library/Application\ Support/Code/User/prompts/

# Linux
ln -s $(pwd)/<file>.instructions.md ~/.config/Code/User/prompts/

# Windows
mklink "%APPDATA%\Code\User\prompts\<file>.instructions.md" "<full-path>\<file>.instructions.md"
```

### Project-Level Instructions

Copy to your project's `.github/copilot-instructions.md`.

### Referencing in Chat

Use `#<filename>` in Copilot Chat to include instructions.

## Naming Convention

- Use lowercase with hyphens: `terraform.instructions.md`
- Always use `.instructions.md` extension
- Be descriptive: `python-fastapi.instructions.md`

## Creating New Instructions

1. Create a file with `.instructions.md` extension
2. Write clear, specific guidelines
3. Test with Copilot Chat before committing
