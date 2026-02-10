#!/bin/bash

# Install git hooks to a target repository

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOKS_DIR="$SCRIPT_DIR/../hooks"

if [ -z "$1" ]; then
    echo "Usage: $0 <target-repo-path>"
    echo "Example: $0 /path/to/your/project"
    exit 1
fi

TARGET_REPO="$1"
TARGET_HOOKS_DIR="$TARGET_REPO/.git/hooks"

if [ ! -d "$TARGET_REPO/.git" ]; then
    echo "Error: $TARGET_REPO is not a git repository"
    exit 1
fi

echo "Installing hooks to: $TARGET_HOOKS_DIR"

# Install pre-commit hooks
if [ -d "$HOOKS_DIR/pre-commit" ]; then
    for hook in "$HOOKS_DIR/pre-commit"/*; do
        if [ -f "$hook" ]; then
            cp "$hook" "$TARGET_HOOKS_DIR/pre-commit"
            chmod +x "$TARGET_HOOKS_DIR/pre-commit"
            echo "  ✓ Installed pre-commit hook"
        fi
    done
fi

# Install commit-msg hooks
if [ -d "$HOOKS_DIR/commit-msg" ]; then
    for hook in "$HOOKS_DIR/commit-msg"/*; do
        if [ -f "$hook" ]; then
            cp "$hook" "$TARGET_HOOKS_DIR/commit-msg"
            chmod +x "$TARGET_HOOKS_DIR/commit-msg"
            echo "  ✓ Installed commit-msg hook"
        fi
    done
fi

echo "Done!"
