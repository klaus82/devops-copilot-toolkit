# AI-Powered Git Hooks

Git hooks enhanced with AI capabilities.

## Available Hooks

| Hook | Description |
|------|-------------|
| `pre-commit/` | Run before commit - lint, format, security checks |
| `commit-msg/` | Validate/enhance commit messages |

## Installation

Use the install script:

```bash
../scripts/install-hooks.sh /path/to/your/repo
```

Or manually copy hooks:

```bash
cp hooks/pre-commit/* /path/to/repo/.git/hooks/
chmod +x /path/to/repo/.git/hooks/*
```

## Creating New Hooks

1. Create a subfolder named after the git hook type
2. Make the script executable
3. Document prerequisites (API keys, tools, etc.)

## Requirements

Some hooks may require:
- GitHub Copilot CLI (`gh copilot`)
- OpenAI API key
- Other AI tools

Check individual hook READMEs for specific requirements.
