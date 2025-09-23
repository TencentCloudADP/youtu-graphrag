# Toolkits

Toolkits are collections of related tools that an agent can use to perform actions. They are the primary way to extend an agent's capabilities.

## `AsyncBaseToolkit`

All toolkits inherit from the `AsyncBaseToolkit` abstract base class. This class provides a standardized interface for creating and managing tools. The core requirement for any toolkit is to implement the `get_tools_map()` method, which returns a dictionary mapping tool names to their corresponding Python functions.

The base class automatically handles the conversion of these functions into `FunctionTool` objects that the agent runner can understand and execute.

All available toolkits are registered in the `TOOLKIT_MAP` dictionary within `utu/tools/__init__.py`.

## Summary of Core Toolkits

Here is a summary of some key toolkits available in the framework:

| Toolkit Class | Provided Tools (Functions) | Core Functionality & Mechanism |
| :--- | :--- | :--- |
| **[SearchToolkit][utu.tools.search_toolkit.SearchToolkit]** | `search`, `web_qa` | Performs web searches using the Serper API and reads webpage content using the Jina API. It can use an LLM to answer questions based on page content. |
| **[DocumentToolkit][utu.tools.document_toolkit.DocumentToolkit]** | `document_qa` | Processes local or remote documents (PDF, DOCX, etc.). It uses the `chunkr.ai` service to parse the document and an LLM to answer questions or provide a summary. |
| **[PythonExecutorToolkit][utu.tools.python_executor_toolkit.PythonExecutorToolkit]** | `execute_python_code` | Executes Python code snippets in an isolated environment using `IPython.core.interactiveshell`. It runs in a separate thread to prevent blocking and can capture outputs, errors, and even `matplotlib` plots. |
| **[BashToolkit][utu.tools.bash_toolkit.BashToolkit]** | `run_bash` | Provides a persistent local shell session using the `pexpect` library. This allows the agent to run a series of commands that maintain state (e.g., current directory). |
| **[ImageToolkit][utu.tools.image_toolkit.ImageToolkit]** | `image_qa` | Answers questions about an image or provides a detailed description. It uses a vision-capable LLM to analyze the image content. |
| **[AudioToolkit][utu.tools.audio_toolkit.AudioToolkit]** | `audio_qa` | Transcribes audio files using an audio model and then uses an LLM to answer questions based on the transcription. |
| **[CodesnipToolkit][utu.tools.codesnip_toolkit.CodesnipToolkit]** | `run_code` | Executes code in various languages (Python, C++, JS, etc.) by sending it to a remote sandbox service (like SandboxFusion) and returning the result. |
<!-- 
| **[FileEditToolkit][utu.tools.file_edit_toolkit.FileEditToolkit]** | `edit_file` | Edits local files by applying a specific `SEARCH/REPLACE` diff format. It includes safety features like filename sanitization and automatic backups. |
| **[ArxivToolkit][utu.tools.arxiv_toolkit.ArxivToolkit]** | `search_papers`, `download_papers` | A wrapper around the `arxiv.py` library to search for and download academic papers from arXiv.org. |
| **[GitHubToolkit][utu.tools.github_toolkit.GitHubToolkit]** | `get_repo_info` | Fetches repository metadata (stars, forks, language, etc.) from the GitHub REST API. |
-->