# Agent Environments

An Environment (`Env`) represents the world in which the agent operates. Its primary responsibilities are to provide the agent with a sense of its current **state** and a set of **tools** to interact with that world.

The framework uses a factory function, `get_env`, to create the appropriate environment based on the agent's configuration file.

## Core Concepts

All environments inherit from the abstract base class `Env`, which defines the core interface:

- `get_state() -> str`: Returns a string describing the current state of the environment. This information is injected into the agent's prompt to provide context.
- `get_tools() -> list[Tool]`: Returns a list of `Tool` objects that the agent can use to interact with the environment.
- `build()` / `cleanup()`: Methods to manage the lifecycle of the environment, such as starting services or cleaning up resources.

---

## Available Environments

Here are the currently available environment implementations.

### `BaseEnv`

This is the simplest and default environment. It can be considered a "null" environment.

- **State**: Provides no state information (returns an empty string).
- **Tools**: Provides no tools (returns an empty list).
- **Use Case**: Used when the agent's task does not require any specific environmental interaction.

### `ShellLocalEnv`

This environment provides the agent with an isolated workspace on the local filesystem.

- **State**: The state string includes the current time, the absolute path to the isolated workspace, and a crucial instruction for the agent: `You can only run bash commands in your workspace!!!`. This helps guide and constrain the agent's behavior.
- **Tools**: This environment does **not** provide tools directly. The agent must be configured separately with tools capable of executing shell commands (e.g., a `bash` tool). The environment's role is to provide the context and workspace for those tools.
- **Isolation**: A unique workspace directory is created for each run session, preventing interference between different tasks.

### `BrowserEnv`

This is a powerful environment that gives the agent control over a fully-featured, interactive web browser.

- **Architecture**: `BrowserEnv` runs a browser automation service inside a **Docker container**. This ensures that each agent session is completely isolated and has a clean, predictable browser environment.
- **State**: The state represents the current content of the web page. It is updated after every action (e.g., clicking an element, navigating to a URL), giving the agent feedback on the result of its last action.
- **Tools**: Tools are provided dynamically by the browser service running in the container. `BrowserEnv` acts as a **proxy**: it discovers the available tools (e.g., `go_to_url`, `click_element`, `input_text`) and makes them available to the agent. When the agent calls a tool, `BrowserEnv` forwards the request to the Docker container for execution.

---

## Configuration

You can specify which environment to use in your agent's configuration file:

```yaml
# In your agent configuration file
env:
  name: shell_local  # Or: browser_docker, base
```
