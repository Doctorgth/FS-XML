> ⚠️ **Disclaimer:** This document is a translation from the original Russian version ([README.ru.md](README.ru.md)) and may contain inaccuracies or minor errors. For the original documentation, please refer to [the Russian README](README.ru.md).

# FS-XML Interpreter

**Safe AI Patch Orchestrator (FS-XML v2.0)**

**English** | [Русский](README.ru.md)

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg)](requirements.txt)
[![Vue 3](https://img.shields.io/badge/Frontend-Vue_3_+_TypeScript-4FC08D.svg)](frontend/package.json)
[![Boosty](https://img.shields.io/badge/Support-Boosty-orange.svg)](https://boosty.to/doctorgth)

A desktop orchestrator (**Python + FastAPI + Vue 3 + PyWebView**) that turns regular AI web chats into safe, semi-autonomous AI agents: controlled project context bundling and one-click multi-file code patching using the **FS-XML v2.0** specification.

---

## Why Use This Program?

### 1. Web Chats as Semi-Autonomous Human-in-the-Loop AI Agents
Most developers already copy code from AI web chats (**Gemini, ChatGPT, Claude, DeepSeek, Qwen**). The model already understands your project structure and is fully capable of creating files and making targeted edits — it just lacks a safe bridge to your disk.

Meanwhile, fully autonomous AI agents inside IDEs come with two major drawbacks:
- **Token burn & unguarded edits:** the agent decides what to read on its own, crawls the entire repository, burns millions of API tokens on unnecessary file reads, and may accidentally rewrite critical code.
- **Working "blind" for hours:** an autonomous agent can spend a long time applying dozens of edits, leaving the project broken or altering business logic behind your back.

**FS-XML Interpreter** gives you full control at every step:
- **Modular isolation:** you decide which files and modules the AI gets to see. If you have a finished module that already does its job, you only need to expose its exported functions/interfaces (or mark critical files as **`Read-Only`**). The AI doesn't even need to know the module's internals — it can cleanly write a new module against it without wasting context or risking breaking working code.
- **Step-by-step verification:** apply a batch of changes in one click and immediately verify the result: **does the program run, did the AI understand you correctly, and did it preserve your logic?**

### 2. Web Chats Without Dozens of Manual Copy-Pastes
Web chats offer huge context windows without per-token API billing, but have no direct disk access.
- Bundle a clean **`context_dump.txt`** directly into your project root in 1 click (**without overwriting your clipboard**).
- Attach the file to the chat, then paste the AI's XML response into the app to apply all changes in 1 click.

### 3. Safety: Snapshots, Rollbacks & 1-Click Error Copy
- **Per-file Rollback & Re-apply** stored in SQLite history with **manual edit detection** (warns you before overwriting changes you made by hand after the AI patch).
- **Fast failure recovery:** clicking an error record in history immediately copies the failed `<fs_search>` / `<fs_replace>` block and the actual file content from disk to your clipboard — just paste it back into the chat.
- **Project Snapshots:** checkpoints of marked files and profile permissions before major refactorings.

---

## Key Features (v2.0)

1. **Projects & Profiles (Separation of Concerns):**
   - Manage multiple projects, change root directories, and open the project folder directly from the top bar.
   - Independent **Profiles** for different tasks (e.g., a `Backend` profile keeps frontend files out of context so the AI stays strictly within its area of responsibility).

2. **Context Tree & Attached Files Viewer:**
   - Tree-view file marking (`W` — `Writable`, `RO` — `Read-Only`) with substring, wildcard (`*.ts`), and regex (`^src/`) search, plus bulk permission actions.
   - Dual-pane **Attached Files Viewer** with search and one-click code copy.

3. **Smart Context Dump (`context_dump.txt`):**
   - Saved directly to `<project_root>/context_dump.txt` without overwriting your clipboard.
   - Automatic binary file skipping (`[BINARY FILE EXCLUDED]`).
   - **"Include unmarked file names"** option — appends a list of paths (`UNMARKED PROJECT STRUCTURE`) so the AI knows other files exist without reading their contents.
   - **"Ignore tests"** option (`test_*`, `*_test`, `*.test.*`, `*.spec.*`) — excludes unmarked test files from the dump and replaces marked test bodies with `# [TEST FILE EXCLUDED - EXISTS ON DISK]`.

4. **Two-Level Ignore System (`fsignore`):**
   - Global (`fsignore_global`) + per-project (`.fsignore`) using `.gitignore` syntax, inline `#` comments, escaped `\#`, and dynamic reload.
   - Excludes heavy folders like `node_modules/`, `.venv/`, `.git/`, `dist/` from scanning and context dumps.

5. **Resilient FS-XML v2.0 Parser & Sandbox (`Sandbox`):**
   - `<fs_create>` (forbids overwriting existing files) and `<fs_edit>` (multiple `<fs_search>`/`<fs_replace>` pairs, trailing-whitespace tolerance, `CRLF`/`LF` preservation, full overwrite via `<all />`).
   - Path traversal protection outside the project root, per-file write permission enforcement, and local-origin CORS filtering.
   - Extensible handler registry (`BaseCommandHandler` + custom commands in `core/handlers/custom/`).

6. **Snapshots & Portable Configuration (`fs_orchestrator_config.json`):**
   - Create and restore snapshots for the active profile or all profiles in a project.
   - Export and import `fs_orchestrator_config.json` to transfer a project, its profiles, and file permissions to another machine.

7. **Desktop UI & Personalization:**
   - Resizable and collapsible side panels, collapsible system log, built-in **Instruction** modal, and background image toggle/selector.

---

## Quick Start

### Running the Ready-Made Application
No installation, compilation, or setup is required — the pre-built **`FS-XML.exe`** launcher is already included in the project root and in the release package (`release/FS-XML.exe`):

1. Download the release (or clone the repository).
2. Run **`FS-XML.exe`**.

<details>
<summary>For Developers: Running from Source, Dev Mode & Building a Release</summary>

#### Development Requirements
- **Python 3.10+** (`fastapi`, `uvicorn[standard]`, `pydantic`, `pywebview`, `pytest`, `httpx`)
- **Node.js / npm** (to build or develop the Vue 3 frontend)

#### Setup & Launch via `.venv`
```bat
install.bat   :: Creates .venv, installs Python/NPM dependencies, and builds frontend\dist
run.bat       :: Rebuilds the frontend and launches desktop_app.py
```

#### Manual Development Mode (Hot Reload)
```bash
# Terminal 1 — Backend API (port 18420)
python server/main.py

# Terminal 2 — Frontend Vite HMR (port 18421)
cd frontend && npm run dev
```

#### Building a New `FS-XML.exe` & Portable Release
1. Place Windows Embeddable Python into `python/` and run **`setup_embed_python.bat`**.
2. Run **`build_exe.bat`** (compiles `launcher.cs` into `FS-XML.exe` via `.NET Framework csc.exe`) or **`build_release.bat`** (builds the frontend, `FS-XML.exe`, and packages everything into `release/`).

</details>

---

## Workflow

```
[ Project on Disk ] ──> (Mark W / RO in Profile) ──> [ Generate context_dump.txt ]
                                                                   │
                                                                   ▼
                                                   [ Dump + Prompt in AI Chat ]
                                                                   │
                                                                   ▼
[ Human Verification ] <── (Click "RUN") <── [ AI XML Response ]
         │
         ├──> Patch Error? ──> [ Click Error in History ] ──> (Copies Search + Disk File)
         └──> Wrong Logic? ──> [ Rollback / Re-apply ] or [ Restore Snapshot ]
```

---

## Tips for Working with AI

1. **Provide the System Prompt Once:**
   Click **КОПИРОВАТЬ ПРОМПТ** (Copy Prompt, loaded from `FS-XML.txt`) and paste it into **System Instructions** (Google AI Studio, API, Custom Instructions) or send it as the first message in your chat.
2. **Paste AI Responses "As-Is":**
   It doesn't matter whether the AI wraps XML in markdown blocks or adds explanations around the tags — copy the entire response and paste it into the central editor. The parser extracts valid commands automatically.
3. **If `Search block not found` Occurs:**
   Click the failed row in the right-hand history panel — the broken search block and the current file from disk are copied to your clipboard. Send them to the AI so it can fix the patch.
4. **`<fs_create>` Is Only for New Files:**
   Existing files must be modified via `<fs_edit>` (use `<all />` inside search for full overwrites).
5. **Keep Chat Context Clean:**
   When sending a fresh `context_dump.txt`, remove outdated dumps from the chat history or start a new conversation so the model doesn't mix up old and new file versions.

---

## FS-XML v2.0 Command Format

### 1. Standard Commands (Always Allowed)

#### Create a new file (`<fs_create>`)
```xml
<fs_create path="src/utils/logger.py">
import datetime

def log(msg: str):
    print(f"[{datetime.datetime.now()}] {msg}")
</fs_create>
```

#### Targeted edit (`<fs_edit>`)
Multiple `<fs_search>` / `<fs_replace>` pairs are supported inside a single `<fs_edit>` block:
```xml
<fs_edit path="src/utils/logger.py">
<fs_search>
def log(msg: str):
    print(f"[{datetime.datetime.now()}] {msg}")
</fs_search>
<fs_replace>
def log(msg: str, level: str = "INFO"):
    print(f"[{datetime.datetime.now()}] [{level}] {msg}")
</fs_replace>
</fs_edit>
```

#### Full file overwrite (`<all />`)
```xml
<fs_edit path="config.py">
<fs_search><all /></fs_search>
<fs_replace>
DEBUG = True
DATABASE_URL = "sqlite:///app.db"
</fs_replace>
</fs_edit>
```

---

### 2. Management Commands (Require the "Management Commands" Flag)

#### What Do They Do and Why Are They Needed?
These commands allow the AI to **automatically manage your context organization**: creating new profiles and changing file access permissions (`Writable` / `Read-Only` / `Unmarked`) so you don't have to manually toggle dozens of files in the tree.

*Example:* you tell the AI: "Create a separate profile for the auth task, set legacy configs to Read-Only, and mark the new routers as Writable" — the model reconfigures the workspace in a single response.

> **Note:** Changing file permissions only affects the **currently active profile**. The AI does not have a command to switch the active profile.

#### How Do They Work and What Do They Affect?
- **Protected by default:** as long as the **"Management Commands"** (`Управляющие команды`) checkbox in the bottom-right panel is **unchecked**, the orchestrator **blocks** all management commands with an access error (meanwhile, standard `<fs_create>` and `<fs_edit>` commands in the same response still execute normally).
- **When enabled:**
  - changes apply to the current session and are **persisted in the SQLite database**;
  - updated permissions appear immediately in the file tree and take effect on the **next `context_dump.txt` generation** and subsequent sandbox write checks.
- **Important:** management commands modify **profile and permission metadata**, not file contents on disk (so per-file rollback in history is not applicable to them).

#### Available Commands

1. **`<fs_profile_create>` — create a new profile:**
   Creates a new configuration profile in the current project (if no profile with that name exists yet).
   ```xml
   <fs_profile_create name="Backend-Focus" />
   ```

2. **`<fs_file_state>` — change a file's state in the active profile:**
   Sets one of the three states (`writable`, `readonly`, or `unmarked`) for the specified file:
   ```xml
   <fs_file_state path="src/config.py" state="readonly" />
   <fs_file_state path="src/api/routes.py" state="writable" />
   <fs_file_state path="src/legacy/old.py" state="unmarked" />
   ```
   - `writable` — include the file in context and allow the AI to edit it;
   - `readonly` — include the file in context strictly for reading (write-protected);
   - `unmarked` — remove the file from the active profile's context.

*(Additionally, developers can extend the system with custom commands via `BaseCommandHandler` in `core/handlers/custom/`.)*

---

## Architecture & Tests

- Detailed project structure: [`архитектура.txt`](архитектура.txt).
- **Run all tests (Backend + Frontend):** `run_all_tests.bat`
  - **Backend (`pytest`):** `python -m pytest backend_tests -v` (`run_backend_tests.bat`)
  - **Frontend (`vitest`):** `cd frontend && npm run test` (`run_web_tests.bat`)

---

## License & Author

- Licensed under the **Apache License 2.0** ([`LICENSE`](LICENSE)). Third-party notices are available in [`NOTICE.md`](NOTICE.md).
- Author: **Doctorgth** (2026) — [GitHub](https://github.com/Doctorgth/FS-XML) | [Boosty](https://boosty.to/doctorgth)


