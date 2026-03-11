# Compression Skill

Skill for compressing infrastructure code and configuration files to reduce token count and optimize context usage.

## Usage

This skill is invoked when you mention:
- "compress"
- "reduce tokens"
- "shrink"
- "optimize context"
- "token savings"
- "minify"

## Features

- **Multi-format support**: Terraform (HCL), YAML, JSON, Markdown, logs
- **Token reduction**: Typically 30-50% savings on config files
- **Cost estimation**: Shows cost savings based on model pricing
- **Pipeline**: Minify → TOON (abbreviations) → Dedup → Distill
- **Safety**: Preserves semantic meaning, reversible with context

## Supported Formats

| Format | Extensions | Typical Savings |
|--------|------------|------------------|
| Terraform | `.tf`, `.tfvars` | 30-50% |
| YAML | `.yaml`, `.yml` | 30-45% |
| JSON | `.json` | 25-40% |
| Markdown | `.md` | 10-30% |
| Logs | `.log`, `.txt` | 40-70% |

## Workflow

1. **Identify files** - What needs compression?
2. **Apply pipeline** - Run compression steps
3. **Report results** - Show token/cost savings
4. **Provide output** - Return compressed content

## Integration

This skill can be used alongside:
- **@terraform-aws**: Compress large Terraform files before delegation
- **Security skill**: Compress code for security reviews
- **FinOps skill**: Track cost savings from reduced token usage

## Files

```
compression/
├── SKILL.md           # Main skill definition
├── README.md          # This file
└── references/        # Additional references (optional)
```

## Requirements

- Python 3.10+
- Token Shield submodule (`token-shield/scripts/compress.py`)
- Dependencies: opentelemetry (optional for metrics)

## Example

```
User: "Compress my Terraform files to save tokens"

→ Run: python token-shield/scripts/compress.py main.tf
→ Report: 44.5% savings ($0.000101 saved)
→ Output: Compressed Terraform code
```
