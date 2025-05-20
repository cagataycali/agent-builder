"""
Unified user input handling module for STRANDS tools.
Uses prompt_toolkit for input features and rich.console for styling.
Includes intelligent assistant that activates on typing pauses.
"""

import asyncio
import concurrent.futures
import copy
import os
from pathlib import Path

from prompt_toolkit import HTML, PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout
from rich.pretty import pprint

# Import the Agent class for creating our typing assistant
from strands import Agent


# Determine history file path
def get_history_file_path():
    # First check environment variable
    history_path = os.environ.get("STRANDS_INPUT_HISTORY_PATH")
    if history_path:
        return history_path

    # Next try ~/.strands/input_history
    home_path = Path.home() / ".strands" / "input_history"
    if home_path.parent.exists() or home_path.parent.mkdir(parents=True, exist_ok=True):
        return str(home_path)

    # Fallback to /tmp/input_history
    return "/tmp/input_history"


# Create a session with persistent history
history_file = get_history_file_path()
session = PromptSession(history=FileHistory(history_file))


async def get_user_input_async(prompt: str, default: str = "", agent=None, typing_timeout: float = 2.5) -> str:
    """
    Asynchronously get user input with smart agent assistance when typing pauses are detected.

    Args:
        prompt: The prompt to show
        default: Default response (default is empty string)
        agent: The Strands agent instance to use for assistance
        typing_timeout: Seconds of pause before triggering the assistant

    Returns:
        str: The user's input response
    """
    typing_timer = None
    current_text = ""
    min_text_length = 5  # Minimum text length to trigger assistant

    async def trigger_assistant_after_pause(text, timeout, buffer):
        try:
            # Wait for the timeout
            await asyncio.sleep(timeout)
            # Don't proceed if we don't have references to the app/buffer
            if not buffer or not buffer.text:
                return

            # Use the agent's message history for context
            await launch_assistant(text, buffer)
        except Exception as e:
            # Silently handle errors without disrupting the user
            print(f"\n(Assistant error: {str(e)})", end="\r")

    async def launch_assistant(text, buffer):
        if not agent:
            return

        # Save current input state (if available)
        if not buffer or not hasattr(buffer, "text"):
            return

        current_input = buffer.text
        cursor_position = buffer.cursor_position

        # Show subtle indicator
        print("\n🤔", end="\r")

        try:
            # Custom system prompt for the typing assistant
            assistant_system_prompt = """
            You are a helpful typing assistant that provides subtle suggestions based on what the user
            is currently typing. Keep suggestions brief, relevant and non-intrusive.

            Don't output long explanations - just offer a quick suggestion, completion, or question
            that might help the user continue their train of thought.
            """

            # Create a separate thread for the assistant agent
            def run_assistant_in_thread():
                # Create a new agent with the parent's model and tools
                # but with our special system prompt
                tools = []
                trace_attributes = {}

                if agent:
                    tools = list(agent.tool_registry.registry.values())
                    trace_attributes = agent.trace_attributes

                assistant_agent = Agent(
                    model=agent.model,
                    tools=tools,
                    system_prompt=agent.system_prompt + "\n\n" + assistant_system_prompt,
                    trace_attributes=trace_attributes,
                    messages=copy.deepcopy(agent.messages),
                    callback_handler=agent.callback_handler,
                    # Don't need a callback handler for this brief interaction
                )

                # Generate suggestion without recording in history
                prompt = f"The user is typing: '{text}'. What is your thought on it?"
                response = assistant_agent(prompt)

                return response

            # Run in thread pool to avoid blocking
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_assistant_in_thread)
                # Set a reasonable timeout to ensure we don't block too long
                suggestion_text = future.result(timeout=10.0)

                # Only display if we got a meaningful response
                if suggestion_text and len(suggestion_text) > 0:
                    # Clear the thinking indicator and show suggestion
                    print("\r" + " " * 10 + "\r", end="")  # Clear the thinking emoji
                    pprint(suggestion_text, end="\r")
        except Exception as e:
            print(e)
            # Silently ignore errors
            pass
        finally:
            # Restore input regardless of success/failure
            if buffer and hasattr(buffer, "text"):
                buffer.text = current_input
                buffer.cursor_position = cursor_position

    try:
        # We'll attach the text change handler after the prompt starts
        # to ensure the buffer exists
        def handle_text_change(buffer):
            nonlocal typing_timer, current_text
            # Cancel previous timer if exists
            if typing_timer and not typing_timer.done():
                typing_timer.cancel()

            # Only trigger if we have some meaningful text and an agent is available
            if agent and buffer and len(buffer.text) > min_text_length and buffer.text != current_text:
                current_text = buffer.text
                # Set new timer
                typing_timer = asyncio.create_task(trigger_assistant_after_pause(buffer.text, typing_timeout, buffer))

        # Use patch_stdout to allow async output during input
        with patch_stdout(raw=True):
            # Start prompt_async without attaching handler first
            response_future = session.prompt_async(
                HTML(f"{prompt} "),
                auto_suggest=AutoSuggestFromHistory(),
                default=default,
                enable_history_search=True,
            )

            # Now that prompt is running, we can safely attach the handler if agent is provided
            if agent and hasattr(session, "app") and hasattr(session.app, "current_buffer"):
                # Attach handler to the current_buffer which is guaranteed to exist
                session.app.current_buffer.on_text_changed += handle_text_change

            # Now wait for the response
            response = await response_future

        # Cancel any pending timer
        if typing_timer and not typing_timer.done():
            typing_timer.cancel()

        return str(response)
    except (KeyboardInterrupt, EOFError):
        return default


def get_user_input(prompt: str, default: str = "", agent=None) -> str:
    """
    Synchronous wrapper for get_user_input_async with agent assistance.

    Args:
        prompt: The prompt to show
        default: Default response (default is empty string)
        agent: The Strands agent instance to use for assistance

    Returns:
        str: The user's input response
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Get result and ensure it's returned as a string
    result = loop.run_until_complete(get_user_input_async(prompt, default, agent))
    return str(result)
