"""Tool for managing the Strands welcome text."""

import os
from pathlib import Path
from typing import Any

from strands.types.tools import ToolResult, ToolUse

# Default welcome text with complete Strands tool building guide
DEFAULT_WELCOME_TEXT = '''*.*
*.*
*.*
*welcome to strands agent builder!*
# 🚀 STRANDS AGENTS SDK: Self-Extending AI Tool Building

## About Agent Builder
I am the Strands Agent Builder - an AI assistant dedicated to helping you build and extend AI tools using the Strands Agents framework. I'm designed to make the development of AI agents more accessible and powerful.

GitHub Repository: https://github.com/strands-agents/agent-builder

## SDKs and Tools

### 📦 SDK Source
https://github.com/strands-agents/sdk-python

### 🧰 Tools Repository
https://github.com/strands-agents/tools

## Installation & Updates:

### 📦 Installing Strands
```bash
pip install strands-agents strands-agents-tools
```

### 🔄 Updating Agent Builder
```bash
pipx install git+https://github.com/strands-agents/agent-builder.git --force
# or
pipx install strands-agent-builder --force
```

## Quick Reference Guide:

### 1️⃣ Core Imports
```python
from strands import Agent, tool
from strands_tools import load_tool, shell, editor

agent = Agent(tools=[load_tool, shell, editor])
```

### 2️⃣ Tool Definition Pattern
```python
from strands import tool

@tool
def my_tool(param1: str, param2: int = 42) -> dict:
    """
    Tool description - explain what it does.

    Args:
        param1: Description of first parameter
        param2: Description of second parameter

    Returns:
        Dictionary with results
    """
    try:
        # Implementation
        result = do_something(param1, param2)
        return {
            "status": "success", 
            "content": [{"text": f"✅ Result: {result}"}]
        }
    except Exception as e:
        return {
            "status": "error",
            "content": [{"text": f"❌ Error: {str(e)}"}]
        }
```

### 3️⃣ Create & Use Tools Instantly

- cwd()/tools/*.py directory is hot-reloaded. I can create tools and use them immediately.
- agent.tool.load_tool(name="tool_name", path="tool_path") allows to load from different directories.

```python
# Create tool
agent.tool.editor(command="create", path="tools/data_tool.py", file_text="...")

# Use immediately - no restart needed
agent.tool.data_tool("parameter")
```

### 4️⃣ Tool Building Process
1. **Identify need** for new capability
2. **Implement** code in tools directory
3. **Use immediately** with agent.tool.tool_name()
4. **Enhance iteratively** without restarts

Available built-in tools:
- memory
- file_read
- file_write
- shell
- editor
- http_request
- python_repl
- calculator
- retrieve
- use_aws
- load_tool
- environment
- use_llm
- think
- journal
- image_reader
- generate_image
- nova_reels
- agent_graph
- swarm
- workflow
- slack
- stop
- speak
- store_in_kb
- strand
- welcome

I'm the Strands Agent Builder, your AI assistant for creating and extending AI tools! Let's build something amazing together.

Type *exit* to quit.'''

TOOL_SPEC = {
    "name": "welcome",
    "description": (
        "Edit and manage Strands welcome text with a backup in cwd()/.welcome. Can also be used as a "
        "shared scratchpad for inter-session communication, status tracking, and coordination between "
        "multiple Strands instances."
    ),
    "inputSchema": {
        "json": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["view", "edit"],
                    "description": "Action to perform: view or edit welcome text",
                },
                "content": {
                    "type": "string",
                    "description": "New welcome text content when action is edit",
                },
            },
            "required": ["action"],
        }
    },
}


def welcome(tool: ToolUse, **kwargs: Any) -> ToolResult:
    """Tool implementation for managing welcome text.

    Beyond simple welcome text management, this tool can be used creatively as:
    1. Inter-session communication channel - Share information between different Strands sessions
    2. Status tracking - Monitor long-running tasks across multiple sessions
    3. Coordination mechanism - Establish handoffs between different instances
    4. Persistent scratchpad - Store temporary information that persists between sessions

    Since all Strands instances read from Path.cwd()/.welcome at startup, information stored
    here is immediately available to any new Strands session.
    """
    tool_use_id = tool["toolUseId"]
    tool_input = tool["input"]

    welcome_path = f"{Path.cwd()}/.welcome"
    action = tool_input["action"]

    try:
        # Create file if doesn't exist
        if action == "edit":
            if "content" not in tool_input:
                raise ValueError("content is required for edit action")

            content = tool_input["content"]
            # Write both to original and backup
            with open(welcome_path, "w") as f:
                f.write(content)

            return {
                "toolUseId": tool_use_id,
                "status": "success",
                "content": [{"text": "Welcome text updated successfully"}],
            }

        elif action == "view":
            # Read from backup if exists, otherwise from default
            if os.path.exists(welcome_path):
                with open(welcome_path, "r") as f:
                    content = f.read()
                msg = "*.*"
            else:
                msg = "*welcome to strands!*"
                content = DEFAULT_WELCOME_TEXT

            return {
                "toolUseId": tool_use_id,
                "status": "success",
                "content": [{"text": f"{msg}\n{content}"}],
            }

        else:
            return {
                "toolUseId": tool_use_id,
                "status": "error",
                "content": [{"text": f"Unknown action: {action}"}],
            }

    except Exception as e:
        return {
            "toolUseId": tool_use_id,
            "status": "error",
            "content": [{"text": f"Error: {str(e)}"}],
        }
