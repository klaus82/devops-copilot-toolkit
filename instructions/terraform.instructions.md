---
applyTo: "infra/**"
---

# Terraform Coding Standards

## Project Context

- **Cloud provider:** AWS (region `eu-west-1`)
- **IaC tool:** Terraform >= 1.10, AWS provider ~> 5.83
- **State backend:** S3 + encryption (`eu-west-1`)
- **Environments (ordered):** `dev` → `test` → `uat` → `preprod` → `prod`
- **Composition root:** `infra/src/` (backend config, provider config, module orchestration)
- **Reusable modules:** `infra/modules/<module-name>/`
- **Environment configs:** `infra/src/env/<env>/tfvars.json`

> **CRITICAL:** Never modify `infra/src/main.tf` provider/backend blocks unless explicitly required.

---

## Directory Structure

```
infra/
├── src/                         # Composition root
│   ├── main.tf                  # Module orchestration & provider config
│   ├── variables.tf             # Root-level input variables
│   ├── outputs.tf               # Root-level outputs
│   ├── local.tf                 # Computed values & local mappings
│   ├── data.tf                  # Data sources
│   ├── security_groups.tf       # Security group definitions
│   ├── env/
│   │   ├── dev/tfvars.json
│   │   ├── test/tfvars.json
│   │   ├── uat/tfvars.json
│   │   ├── preprod/tfvars.json
│   │   └── prd/tfvars.json
│   └── unit-tests/              # Native Terraform tests (1.6+)
└── modules/
    └── <module-name>/           # Reusable resource modules
        ├── main.tf
        ├── variables.tf
        ├── outputs.tf
        └── README.md
```

---

## Required Files in Every Module

| File | Purpose |
|------|---------|
| `main.tf` | Resource definitions, module calls, data sources |
| `variables.tf` | Input variable declarations |
| `outputs.tf` | Output value declarations |
| `README.md` | Usage documentation |

**Optional files (add when needed):**

| File | When to Use |
|------|-------------|
| `locals.tf` | Complex local value calculations |
| `data.tf` | When `main.tf` gets large — separate data sources |
| `versions.tf` | Provider/Terraform version pins (if module requires its own) |
| `providers.tf` | Only when module needs a non-default provider alias |

> `terraform.tfvars` and `backend.tf` belong at the **composition root only** — never inside modules.

---

## Resource Block Ordering

Arguments inside a resource block **must** follow this strict order:

1. `count` or `for_each` — **always first**, blank line after
2. Core arguments — alphabetical or logically grouped
3. `tags` — last real argument
4. `depends_on` — after tags, only when implicit dependencies are insufficient
5. `lifecycle` — at the very end

```hcl
# ✅ GOOD
resource "aws_nat_gateway" "this" {
  count = var.create_nat_gateway ? 1 : 0

  allocation_id = aws_eip.this[0].id
  subnet_id     = aws_subnet.public[0].id

  tags = {
    Name        = "${var.name}-nat"
    Environment = var.environment
  }

  depends_on = [aws_internet_gateway.this]

  lifecycle {
    create_before_destroy = true
  }
}
```

---

## Variable Block Ordering

Fields inside a `variable` block **must** follow this order:

1. `description` — **always required, never omit**
2. `type`
3. `default`
4. `sensitive` (when `true`)
5. `nullable` (when `false`)
6. `validation`

```hcl
variable "environment" {
  description = "Deployment environment name"
  type        = string
  default     = "dev"
  nullable    = false

  validation {
    condition     = contains(["dev", "test", "uat", "preprod", "prod"], var.environment)
    error_message = "Environment must be one of: dev, test, uat, preprod, prod."
  }
}
```

---

## Naming Conventions

### Variables

Use **context-specific** names — never generic ones:

```hcl
# ✅ GOOD
var.vpc_cidr_block
var.database_instance_class
var.ecs_cluster_name

# ❌ BAD
var.name
var.type
var.value
```

### Outputs

Pattern: `{resource}_{attribute}` — use plurals for lists:

```hcl
output "security_group_id" {
  description = "The ID of the security group"
  value       = try(aws_security_group.this[0].id, "")
}

output "private_subnet_ids" {
  description = "List of private subnet IDs"
  value       = aws_subnet.private[*].id
}
```

### Resources & Data Sources

- Use `this` as the name when a module creates a **single** instance of a resource type.
- Use descriptive names when multiple resources of the same type exist.

---

## `count` vs `for_each`

### Use `count` for simple boolean toggles:

```hcl
resource "aws_nat_gateway" "this" {
  count = var.create_nat_gateway ? 1 : 0
}
```

### Use `for_each` for collections where items may be added/removed:

```hcl
module "databases" {
  for_each = var.backend_db_config_map
  source   = "../modules/database"
  # ...
}
```

**Why?** Removing an item from a `count`-based list reshuffles all subsequent indices, causing unnecessary destroys/recreates. `for_each` only affects the specific key being changed.

---

## Modern Terraform Patterns

### Use `try()` for safe access

```hcl
# ✅ Modern
output "security_group_id" {
  value = try(aws_security_group.this[0].id, "")
}

# ❌ Legacy — avoid
output "security_group_id" {
  value = element(concat(aws_security_group.this.*.id, [""]), 0)
}
```

### Use `optional()` for object attributes (Terraform 1.3+)

```hcl
variable "database_config" {
  description = "Database configuration"
  type = object({
    name             = string
    engine           = string
    instance_class   = string
    backup_retention = optional(number, 7)
    tags             = optional(map(string), {})
  })
}
```

### Use `locals` for computed values and common tags

```hcl
locals {
  common_tags = merge(var.tags, {
    Environment = var.env
    ManagedBy   = "Terraform"
  })
}
```

---

## Provider & Version Constraints

- Pin the **minor** version with `~>` to allow patch updates only.
- The root composition defines provider versions; modules should not re-pin unless they need a separate provider alias.

```hcl
terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.83.0"
    }
  }
}
```

---

## Tagging Strategy

All taggable resources **must** receive tags via the provider `default_tags` block plus any resource-specific tags. The provider is configured with:

```hcl
provider "aws" {
  region = "eu-west-1"
  default_tags {
    tags = {
      appenv    = "${var.app_name}-${var.env}"
      bgrp      = var.bgrp
      env       = var.env
      managedby = "Terraform"
    }
  }
}
```

Add resource-specific `Name` tags where appropriate:

```hcl
tags = {
  Name = "${var.app_name}-${var.env}-<resource-descriptor>"
}
```

---

## Environment Management

- Each environment has its own `infra/src/env/<env>/tfvars.json`.
- Environment order is **mandatory**: `dev` → `test` → `uat` → `preprod` → `prod` (mapped to `prd` folder).
- Changes to `tfvars.json` must be reflected across all relevant environments.
- Use `make <env>` to init + plan for a given environment:

```bash
make dev      # ENVIRONMENT=dev
make test     # ENVIRONMENT=test
make uat      # ENVIRONMENT=uat
make prd      # ENVIRONMENT=prd
```

---

## Security Best Practices

### Never store secrets in code or state

- Use AWS Secrets Manager or SSM Parameter Store — reference via `data` sources or module outputs.
- Mark sensitive variables with `sensitive = true`.
- Never hard-code credentials, API keys, or passwords.

### Encryption at rest

- S3 buckets: always enable server-side encryption.
- RDS: enable `storage_encrypted` and use KMS keys.
- CloudWatch Logs: encrypt with KMS.

### Least-privilege security groups

- Never use `0.0.0.0/0` for ingress unless behind a WAF.
- Prefer security-group-to-security-group references over CIDR blocks.
- Restrict ports to only what the service needs.

### Remote state

- Always use S3 backend with encryption enabled.
- Never commit `.tfstate` files.

---

## Static Analysis & Validation

Run these checks **before** every commit:

```bash
# Format check
terraform fmt -recursive -check

# Validation
terraform -chdir=infra/src validate

# Security scanning (Checkov)
checkov -d infra/ --framework terraform

# Linting
tflint --init && tflint
```

The project includes Azure Pipeline templates for automated scanning in CI — see `static-analysis/checkov.yml` and `static-analysis/tflint.yml`.

---

## Anti-patterns to Avoid

| Anti-pattern | Problem | Solution |
|--------------|---------|----------|
| Hard-coded values in modules | Locked to one environment | Make everything configurable via variables |
| God modules (do everything) | Hard to test, reuse, maintain | Break into focused resource modules |
| `count` for dynamic collections | Removing items recreates subsequent resources | Use `for_each` |
| Secrets in state or variables | Security risk | Use Secrets Manager / SSM + `sensitive = true` |
| No remote state | No collaboration, no locking | Always use S3 backend |
| Skipping `description` on variables | Poor discoverability, no docs | Always add meaningful descriptions |
| Using `lookup()` where `try()` works | Legacy pattern, less readable | Prefer `try()` |
| Wildcard provider versions | Non-reproducible builds | Pin with `~>` constraints |

---

## Module Development Checklist

When creating or modifying a module:

- [ ] All variables have `description`
- [ ] Variable blocks follow the prescribed field order
- [ ] Resource blocks follow the prescribed argument order
- [ ] `for_each` used for collections, `count` only for boolean toggles
- [ ] Outputs use `try()` for conditional resources
- [ ] `README.md` documents purpose, inputs, outputs, and usage example
- [ ] No hard-coded values — everything parameterized
- [ ] Tags propagated via variables or `local.common_tags`
- [ ] `terraform fmt` passes cleanly
- [ ] `terraform validate` passes
- [ ] Checkov scan produces no unacknowledged findings
