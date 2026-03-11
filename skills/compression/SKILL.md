---
name: compress-context
description: >
  Compression skill for reducing token count in infrastructure code and config files.
  Use this skill to compress Terraform, YAML, JSON, HCL, or other DevOps configuration files
  before sending to agents. This saves tokens and reduces context window usage.
  Trigger on: "compress", "reduce tokens", "shrink", "optimize context", "token savings",
  "minify", "compact"
compatibility: "Requires: Python 3.10+, token-shield/scripts/compress.py"
---

# Compression Skill

A skill for compressing infrastructure code and configuration files to reduce token count,
save costs, and optimize context window usage.

---

## When to Use

Use this skill when:
- User asks to compress, reduce tokens, or shrink files
- Sending large Terraform/CloudFormation configs to agents
- Context window is filling up with verbose config files
- User wants to optimize costs on LLM usage
- Before delegating to @terraform-aws with large files

---

## Workflow

```
1. Identify Files    → What files need compression?
2. Apply Pipeline    → Run compression steps (minify → TOON → dedup)
3. Report Results    → Show token savings and cost reduction
4. Provide Output    → Return compressed content
```

---

## Compression Pipeline

The compression runs through these steps (in order):

| Step | Description | Applies To |
|------|-------------|------------|
| **Minify** | Strip comments, whitespace, optional blocks | YAML, JSON, HCL, Terraform |
| **TOON** | Abbreviate verbose DevOps keys (e.g., `aws_instance` → `aws_i`) | YAML, JSON, HCL |
| **Dedup** | Collapse repeated lines/blocks | All formats |
| **Distill** | Extract unique patterns from logs | Logs only (`.log`, `.txt`) |

---

## Supported Formats

| Format | Extensions | Pipeline Applied |
|--------|------------|------------------|
| Terraform | `.tf`, `.tfvars` | minify → toon → dedup |
| YAML | `.yaml`, `.yml` | minify → toon → dedup |
| JSON | `.json` | minify → toon → dedup |
| HCL | `.hcl`, `.tf` | minify → toon → dedup |
| Markdown | `.md` | dedup only |
| Logs | `.log`, `.txt`, `.out` | dedup → distill |

---

## Usage

### Command Line

```bash
# Compress a Terraform file
python token-shield/scripts/compress.py main.tf

# Compress YAML with custom model for cost estimation
python compress.py manifest.yaml --model gpt-4.1-mini

# Compress logs
python compress.py app.log --format log

# Skip specific pipeline steps
python compress.py config.yaml --skip toon
```

### In Conversation

When user asks to compress files:
1. Ask for the file(s) or path to compress
2. Run the compression tool
3. Report the savings
4. Provide the compressed output

---

## Output Interpretation

### Shield Report Example

```
╔══════════════════════════════════════════════════════╗
║              TOKEN SHIELD  ·  Shield Report          ║
╠══════════════════════════════════════════════════════╣
║  Format       : hcl                                   ║
║  Pipeline     : minify → toon → dedup                 ║
╠══════════════════════════════════════════════════════╣
║  Chars    15,234 →  8,456   saved 44.5%               ║
║  Tokens    3,808 →  2,114   saved 44.5%               ║
║  Cost    $0.000228 → $0.000127                        ║
║  Saved   $0.000101  (gpt-4.1-mini)                    ║
╚══════════════════════════════════════════════════════╝
  ✔ Significant savings — safe to proceed with compressed payload.
```

### Savings Assessment

| Savings | Action |
|---------|--------|
| ≥40% | Significant savings - safe to proceed |
| ≥15% | Moderate savings applied |
| <15% | Minimal savings - input already compact |

---

## Best Practices

1. **Always compress before delegating** large configs to @terraform-aws
2. **Use --skip distill** for code/config files (distill is for logs only)
3. **Review compressed output** to ensure it still makes sense
4. **Preserve original** if you need to reference exact formatting
5. **Use with FinOps skill** to estimate cost savings from reduced token usage

---

## Integration Points

### With DevOps Orchestrator

Before delegating to agents, consider using compression:
- @terraform-aws: Compress Terraform files first
- Security skill: Compress code being reviewed
- FinOps skill: Compress configs before analysis
- @github-actions: Compress workflow files

### Cost Optimization

Combine with FinOps skill:
1. Compress files to reduce tokens
2. Use smaller/faster models where possible
3. Track cumulative savings across sessions

---

## Technical Notes

- **TOON mappings**: See `scripts/toon_converter.py` for abbreviation rules
- **Minify rules**: See `scripts/minify_config.py` for format-specific stripping
- **Dedup**: Uses smart line collapsing, preserves semantic meaning
- **Distill**: For logs only - extracts unique error/warning patterns
- **Token estimation**: ~4 characters per token (varies by model)

---

## Error Handling

If compression fails:
1. Check file format is supported
2. Try skipping TOON step (`--skip toon`) for complex syntax
3. Verify Python 3.10+ is available
4. Check required dependencies are installed

---

## Reference

- Token Shield: https://github.com/anomalyco/token-shield
- Compress.py location: `token-shield/scripts/compress.py`
