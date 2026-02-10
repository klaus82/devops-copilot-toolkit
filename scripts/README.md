# Scripts

Utility scripts for managing the toolkit and development workflows.

## Available Scripts

### `install-hooks.sh`

Installs git hooks from this toolkit to a target repository.

```bash
./install-hooks.sh /path/to/your/project
```

### `pre-commit-terraform.sh`

A comprehensive Terraform pre-commit hook that enforces best practices and coding standards.

**Checks performed:**

| Check | Description |
|-------|-------------|
| `terraform fmt` | Ensures all `.tf` files are properly formatted |
| `terraform validate` | Validates Terraform configuration (when `infra/src/` files staged) |
| Variable descriptions | Verifies all variables have a `description` attribute |
| Resource block ordering | Ensures `count`/`for_each` appears first in resource blocks |
| Hard-coded secrets | Flags potential passwords/keys in plain text |
| TFLint | Runs TFLint linter (if installed) |
| Checkov | Runs Checkov security scan (if installed) |
| Copilot Review | AI-powered review against best practices (if `gh copilot` available) |

**Installation:**

```bash
# Copy to your repo's git hooks
cp pre-commit-terraform.sh /path/to/repo/.git/hooks/pre-commit
chmod +x /path/to/repo/.git/hooks/pre-commit
```

**Environment Variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `COPILOT_REVIEW` | `true` | Set to `false` to skip Copilot AI review |

**Optional Dependencies:**

- [TFLint](https://github.com/terraform-linters/tflint) - Terraform linter
- [Checkov](https://www.checkov.io/) - Infrastructure security scanner
- [GitHub CLI](https://cli.github.com/) with Copilot extension - AI-powered review

## Adding New Scripts

1. Create the script with a descriptive name
2. Add a shebang (`#!/bin/bash` or `#!/usr/bin/env bash`)
3. Make it executable: `chmod +x script-name.sh`
4. Document it in this README
