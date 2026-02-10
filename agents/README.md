# Copilot Agents

Custom Copilot agents for specific workflows and tasks.

## Structure

Each agent should be in its own folder:

```
agents/
└── <agent-name>/
    ├── README.md           # Usage instructions
    ├── agent.yml           # Agent manifest (for Copilot Extensions)
    ├── instructions.md     # Prompt instructions
    └── tools/              # Custom MCP tools (optional)
```

## Creating a New Agent

1. Create a new folder with the agent name
2. Add an `instructions.md` with the agent's system prompt
3. Add a `README.md` explaining the agent's purpose and usage
4. Optionally add `agent.yml` for Copilot Extensions configuration

## Example Agent Structure

```yaml
# agent.yml
name: code-reviewer
description: Reviews code for best practices and security issues
instructions: instructions.md
```
