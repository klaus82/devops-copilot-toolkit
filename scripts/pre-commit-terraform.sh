#!/usr/bin/env bash
# =============================================================================
# Pre-commit hook: Terraform Best Practices Check
#
# Runs static analysis on staged .tf files and optionally invokes a GitHub
# Copilot agent review against the project's Terraform coding standards.
#
# Install: make install-hooks
# =============================================================================
set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

REPO_ROOT="$(git rev-parse --show-toplevel)"
INSTRUCTIONS_FILE="$REPO_ROOT/.github/instructions/terraform.instructions.md"
FAILED=0

# ── Collect staged .tf files ─────────────────────────────────────────────────
STAGED_TF_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\.tf$' || true)

if [[ -z "$STAGED_TF_FILES" ]]; then
  echo -e "${GREEN}No Terraform files staged — skipping TF checks.${NC}"
  exit 0
fi

echo -e "${CYAN}══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Terraform Pre-commit Checks${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "Staged .tf files:"
echo "$STAGED_TF_FILES" | sed 's/^/  • /'
echo ""

# ── Helper ───────────────────────────────────────────────────────────────────
run_check() {
  local label="$1"
  shift
  echo -e "${CYAN}▸ ${label}${NC}"
  if "$@"; then
    echo -e "  ${GREEN}✔ Passed${NC}"
  else
    echo -e "  ${RED}✘ Failed${NC}"
    FAILED=1
  fi
  echo ""
}

# ─────────────────────────────────────────────────────────────────────────────
# 1. terraform fmt
# ─────────────────────────────────────────────────────────────────────────────
check_fmt() {
  local unformatted=()
  for f in $STAGED_TF_FILES; do
    if ! terraform fmt -check -diff "$REPO_ROOT/$f" > /dev/null 2>&1; then
      unformatted+=("$f")
    fi
  done
  if [[ ${#unformatted[@]} -gt 0 ]]; then
    echo -e "  ${RED}Unformatted files:${NC}"
    printf '    %s\n' "${unformatted[@]}"
    echo -e "  ${YELLOW}Run: terraform fmt -recursive infra/${NC}"
    return 1
  fi
}
run_check "Terraform Format (terraform fmt -check)" check_fmt

# ─────────────────────────────────────────────────────────────────────────────
# 2. terraform validate (only when composition root files are staged)
# ─────────────────────────────────────────────────────────────────────────────
if echo "$STAGED_TF_FILES" | grep -q '^infra/src/'; then
  check_validate() {
    terraform -chdir="$REPO_ROOT/infra/src" validate -no-color 2>&1 | tail -1
  }
  run_check "Terraform Validate (infra/src)" check_validate
fi

# ─────────────────────────────────────────────────────────────────────────────
# 3. Variable description check
#    Every variable block must have a `description` argument.
# ─────────────────────────────────────────────────────────────────────────────
check_variable_descriptions() {
  local bad_files=()
  for f in $STAGED_TF_FILES; do
    # Only check variables.tf files
    [[ "$(basename "$f")" == "variables.tf" ]] || continue
    # Look for variable blocks without a description
    if awk '
      /^variable\s+"/ { in_var=1; has_desc=0; var_line=NR; var_name=$0; next }
      in_var && /description\s*=/ { has_desc=1 }
      in_var && /^\}/ {
        if (!has_desc) { print FILENAME ":" var_line ": " var_name; exit 1 }
        in_var=0
      }
    ' "$REPO_ROOT/$f"; then
      bad_files+=("$f")
    fi
  done
  if [[ ${#bad_files[@]} -gt 0 ]]; then
    echo -e "  ${RED}Variables missing 'description':${NC}"
    printf '    %s\n' "${bad_files[@]}"
    return 1
  fi
}
run_check "Variable Descriptions (all variables.tf)" check_variable_descriptions

# ─────────────────────────────────────────────────────────────────────────────
# 4. Resource block ordering lint
#    count/for_each must appear as the first argument in a resource block.
# ─────────────────────────────────────────────────────────────────────────────
check_resource_ordering() {
  local violations=()
  for f in $STAGED_TF_FILES; do
    # Find resource blocks where count/for_each is NOT the first argument
    result=$(awk '
      /^resource\s+"/ { in_res=1; first_arg=1; res_line=NR; res_name=$0; next }
      in_res && /^\s*#/ { next }           # skip comments
      in_res && /^\s*$/ { next }           # skip blank lines
      in_res && first_arg && /^\s*(count|for_each)\s*=/ { first_arg=0; next }
      in_res && first_arg && /^\s*[a-z_]+\s*=/ {
        # First real arg is NOT count/for_each — check if block uses count/for_each later
        has_meta=0; first_arg=0; next
      }
      in_res && !first_arg && /^\s*(count|for_each)\s*=/ {
        print FILENAME ":" NR ": count/for_each should be first argument in resource block"
        found=1
      }
      in_res && /^\}/ { in_res=0 }
    ' "$REPO_ROOT/$f" 2>/dev/null)
    if [[ -n "$result" ]]; then
      violations+=("$result")
    fi
  done
  if [[ ${#violations[@]} -gt 0 ]]; then
    printf '    %s\n' "${violations[@]}"
    return 1
  fi
}
run_check "Resource Block Ordering (count/for_each first)" check_resource_ordering

# ─────────────────────────────────────────────────────────────────────────────
# 5. No hard-coded secrets
#    Flag obvious hard-coded passwords / keys in .tf files.
# ─────────────────────────────────────────────────────────────────────────────
check_no_hardcoded_secrets() {
  local found=0
  for f in $STAGED_TF_FILES; do
    matches=$(grep -nEi '(password|secret_key|access_key|api_key)\s*=\s*"[^"$]' "$REPO_ROOT/$f" 2>/dev/null | grep -v '#.*noqa' || true)
    if [[ -n "$matches" ]]; then
      echo -e "  ${RED}Potential hard-coded secrets in $f:${NC}"
      echo "$matches" | sed 's/^/    /'
      found=1
    fi
  done
  return $found
}
run_check "No Hard-coded Secrets" check_no_hardcoded_secrets

# ─────────────────────────────────────────────────────────────────────────────
# 6. TFLint (if available)
# ─────────────────────────────────────────────────────────────────────────────
if command -v tflint &> /dev/null; then
  # Determine which module directories have changed files
  CHANGED_DIRS=$(echo "$STAGED_TF_FILES" | xargs -I{} dirname {} | sort -u)
  check_tflint() {
    local lint_failed=0
    for dir in $CHANGED_DIRS; do
      if [[ -d "$REPO_ROOT/$dir" ]]; then
        if ! tflint --chdir="$REPO_ROOT/$dir" --no-color 2>&1; then
          lint_failed=1
        fi
      fi
    done
    return $lint_failed
  }
  run_check "TFLint" check_tflint
else
  echo -e "${YELLOW}▸ TFLint: skipped (not installed)${NC}"
  echo ""
fi

# ─────────────────────────────────────────────────────────────────────────────
# 7. Checkov (if available)
# ─────────────────────────────────────────────────────────────────────────────
if command -v checkov &> /dev/null; then
  check_checkov() {
    checkov -d "$REPO_ROOT/infra" \
      --framework terraform \
      --quiet \
      --compact \
      --skip-path infra/src/.terraform 2>&1 | tail -20
  }
  run_check "Checkov Security Scan" check_checkov
else
  echo -e "${YELLOW}▸ Checkov: skipped (not installed)${NC}"
  echo ""
fi

# ─────────────────────────────────────────────────────────────────────────────
# 8. GitHub Copilot Agent Review (if gh + copilot extension available)
#    Sends changed files to Copilot for a best-practices review using
#    the project's terraform.instructions.md as context.
# ─────────────────────────────────────────────────────────────────────────────
COPILOT_REVIEW=${COPILOT_REVIEW:-true}

if [[ "$COPILOT_REVIEW" == "true" ]] && command -v gh &> /dev/null && gh copilot --help &> /dev/null 2>&1; then
  echo -e "${CYAN}▸ GitHub Copilot Agent Review${NC}"

  # Build a file list for Copilot
  FILE_CONTENTS=""
  for f in $STAGED_TF_FILES; do
    FILE_CONTENTS+="
--- FILE: $f ---
$(cat "$REPO_ROOT/$f")
"
  done

  COPILOT_PROMPT="You are a Terraform code reviewer. Review the following staged Terraform files against these best practices:

1. Resource blocks: count/for_each must be the FIRST argument, then other args, tags last, depends_on after tags, lifecycle at the end.
2. Variable blocks: description (required) → type → default → sensitive → nullable → validation.
3. Naming: context-specific variable names (not generic), output pattern {resource}_{attribute}, plural for lists.
4. Use for_each for collections, count only for boolean toggles.
5. Use try() not legacy element(concat(...)).
6. Use optional() for object attributes.
7. All variables must have description.
8. No hard-coded secrets, no wildcard provider versions.
9. Tags must be present on all taggable resources.
10. Encryption enabled on storage resources.

For each issue found, output:
  [FILE:LINE] SEVERITY: description

If everything looks good, output: ✔ All files follow Terraform best practices.

Files to review:
$FILE_CONTENTS"

  # Run the review — non-blocking (don't fail the commit on Copilot errors)
  if REVIEW_OUTPUT=$(echo "$COPILOT_PROMPT" | gh copilot suggest -t shell 2>&1); then
    echo "$REVIEW_OUTPUT" | sed 's/^/  /'
  else
    echo -e "  ${YELLOW}Copilot review unavailable — skipping.${NC}"
  fi
  echo ""
else
  if [[ "$COPILOT_REVIEW" == "true" ]]; then
    echo -e "${YELLOW}▸ Copilot Review: skipped (gh copilot not available)${NC}"
    echo ""
  fi
fi

# ── Summary ──────────────────────────────────────────────────────────────────
echo -e "${CYAN}══════════════════════════════════════════════════════════════${NC}"
if [[ "$FAILED" -eq 1 ]]; then
  echo -e "${RED}  ✘ Pre-commit checks FAILED — commit blocked.${NC}"
  echo -e "${RED}    Fix the issues above and stage the changes again.${NC}"
  echo -e "${CYAN}══════════════════════════════════════════════════════════════${NC}"
  exit 1
else
  echo -e "${GREEN}  ✔ All Terraform pre-commit checks passed.${NC}"
  echo -e "${CYAN}══════════════════════════════════════════════════════════════${NC}"
  exit 0
fi
