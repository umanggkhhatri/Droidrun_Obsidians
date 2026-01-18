# Obsidians_Droidrun - Complete Agent Context Document

> **Purpose**: This document provides complete context for AI agents working on this project. It covers architecture, critical implementation details, known issues, and the exact state of the codebase.

---

## 1. Project Overview

**What it does**: A social media automation system that posts content to Threads (Instagram's Twitter competitor) using an Android device controlled via DroidRun.

**Core Flow**:

1. User enters description + links + media instructions in web UI
2. Links are crawled for content (HTTP-based, not device)
3. Description + crawled content → transformed by Google Gemini LLM
4. Transformed text + media instructions → sent to DroidRun agent
5. DroidRun agent controls Android device to post to Threads

**Tech Stack**:

- Backend: Flask (Python)
- LLM: Google Gemini 2.5 Pro via `google.genai` SDK
- Device Automation: DroidRun library with Portal app on Android
- Frontend: Vanilla HTML/CSS/JS with Server-Sent Events (SSE)

---

## 2. Directory Structure

```
/Users/anirudh/Obsidians_Droidrun/
├── web/
│   ├── app.py                 # Flask server, main entry point
│   ├── templates/
│   │   └── index.html         # Web UI
│   └── static/                # CSS/JS assets
├── core/
│   ├── base_agent.py          # BasePlatformAgent class, DroidRun integration
│   ├── content_transformer.py # LLM transformation using Gemini
│   ├── link_crawler.py        # HTTP-based URL crawler
│   └── models.py              # Data models (Content, PostResult)
├── agents/
│   ├── threads_agent.py       # ThreadsAgent - main posting agent
│   ├── instagram_agent.py     # (Not actively used)
│   ├── twitter_agent.py       # (Not actively used)
│   └── linkedin_agent.py      # (Not actively used)
├── config/
│   └── settings.py            # App configuration
├── utils/
│   └── __init__.py            # Logging utilities
├── .env                       # API keys (GOOGLE_API_KEY)
├── .gitignore                 # Excludes .env, trajectories/, etc.
└── main.py                    # CLI entry point (alternative to web)
```

---

## 3. Critical Files Deep Dive

### 3.1 `web/app.py` - Flask Server

**Key Responsibilities**:

- Serves web UI at `/`
- Handles POST requests at `/api/post`
- Streams progress via SSE at `/api/progress`
- Orchestrates the entire posting flow

**Important Flow in `/api/post`**:

```python
# Step 1: Extract URLs from text and links fields
all_urls = extract_urls_from_text(text) + extract_urls_from_text(links)

# Step 2: Crawl URLs (HTTP-based, NOT device-based)
crawler = LinkCrawler(max_links_per_page=5, timeout=15)
for url in all_urls[:3]:
    crawled_content += crawler.crawl_url(url)

# Step 3: Combine description + crawled content
combined_content = f"USER DESCRIPTION:\n{text}\n\nCRAWLED LINK CONTENT:{crawled_content}"

# Step 4: Transform with LLM
transformed_text = await transform_content_with_llm(combined_content, droidrun_config)

# Step 5: Pass to ThreadsAgent
content_dict = {"text": transformed_text, "media_source_instructions": media_instructions}
result = await threads_agent.prepare_and_post(content_dict, context)
```

**SSE Streaming**:

- `emit_progress(step, total, message, details)` - Progress updates
- `emit_log(message, log_type)` - Log messages to web terminal
- `set_log_callback(emit_log)` - Connects base_agent logs to web

**Environment Loading**:

```python
from dotenv import load_dotenv
load_dotenv()  # Loads .env file at startup
```

---

### 3.2 `core/base_agent.py` - DroidRun Integration

**Class**: `BasePlatformAgent` - Abstract base class for all platform agents

**Critical Method**: `_run_droidrun_agent(goal, timeout, variables, custom_tools)`

**Custom Tools Pattern** (CRITICAL - this is how to pass data to DroidRun):

```python
# Variables are passed to DroidAgent and stored in shared_state.custom_variables
agent = DroidAgent(
    goal=goal,
    config=self.config,
    variables={"post_text": full_text},  # Stored in shared_state.custom_variables
    custom_tools=tools_to_use
)

# Custom tool accesses via shared_state.custom_variables
def get_post_text(*, shared_state=None, **kwargs) -> str:
    if shared_state:
        return shared_state.custom_variables.get("post_text", "")
    return ""

custom_tools = {
    "get_post_text": {
        "arguments": [],
        "description": "Get the post text content",
        "function": get_post_text
    }
}
```

**Event Streaming** (filtered for clean terminal output):

```python
async for event in handler.stream_events():
    name = event.__class__.__name__
    # Only emit thoughts (💭) and actions (🖱️)
    if name == "ExecutorActionEvent":
        # thought, description
    elif name == "CodeActResponseEvent":
        # thought
    elif "ActionEvent" in name:
        # action
```

**Log Callback System**:

```python
_log_callback = None

def set_log_callback(callback):
    global _log_callback
    _log_callback = callback

def emit_agent_log(message, log_type='info'):
    if _log_callback:
        _log_callback(message, log_type)
```

---

### 3.3 `core/content_transformer.py` - LLM Transformation

**Function**: `transform_content_with_llm(content, config, model="gemini-2.5-pro")`

**SDK**: Uses `google.genai` (NOT the deprecated `google.generativeai`)

```python
from google import genai
client = genai.Client(api_key=api_key)
response = client.models.generate_content(model=model, contents=prompt)
```

**API Key Loading**:

```python
api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
```

**Prompt Structure**:

- Target length: 400-600 characters
- Style: Conversational, authentic, human-like
- Output: Direct post text, no meta-commentary
- Includes cleanup for LLM prefixes like "Here's the post:"

**Cleanup Logic**:

```python
cleanup_prefixes = [
    "Here's the transformed post:",
    "Here's the post:",
    "Here is the post:",
    "Transformed post:",
    "Post:",
]
for prefix in cleanup_prefixes:
    if transformed.lower().startswith(prefix.lower()):
        transformed = transformed[len(prefix):].strip()
```

---

### 3.4 `core/link_crawler.py` - HTTP Crawler

**Class**: `LinkCrawler` - HTTP-based crawler using requests + BeautifulSoup

**Key Methods**:

- `crawl_url(url)` - Crawls main page + first-level internal links
- `_fetch_page(url)` - Single page fetch
- `_extract_text(soup, url)` - Extracts title, meta, headings, paragraphs
- `_extract_internal_links(soup, base_url)` - Gets same-domain links

**Helper Function**:

```python
def extract_urls_from_text(text: str) -> List[str]:
    """Extract URLs from text using regex"""
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    urls = re.findall(url_pattern, text)
    return list(set(cleaned_urls))
```

**Dependencies**: `requests`, `beautifulsoup4`, `lxml`

---

### 3.5 `agents/threads_agent.py` - Threads Posting Agent

**Class**: `ThreadsAgent(BasePlatformAgent)`

**Key Methods**:

- `_prepare_content(content, context)` - Prepares text for posting
- `_post_to_platform(prepared_content, media_urls)` - Executes the post

**Media-First Flow** (when media_source_instructions provided):

1. Agent collects media from device (e.g., Google Photos)
2. Uses share sheet to share media to Threads
3. Threads composer opens with media attached
4. Agent calls `get_post_text()` tool to get transformed text
5. Agent types text into composer
6. Agent publishes post

**Goal Structure**:

```python
goal = f"""
Create a Threads post using media collected FIRST, then add text.

Media collection (priority):
1) Follow these EXACT instructions: {media_instruction}
2) Use system share sheet to share to Threads (com.instagram.barcelona)

Compose in Threads:
3) Call get_post_text() to retrieve the post content ({len(full_text)} characters)
4) Store the returned text: post_content = get_post_text()
5) Type the ENTIRE returned text into composer
6) Publish the post.

CRITICAL: Use ONLY what get_post_text() returns. Do NOT generate your own text.
"""
```

**Variables Passed to Agent**:

```python
agent_variables = {
    "post_text": full_text,  # The LLM-transformed text
    "thread_items": thread,
    "thread_items_json": thread_str
}
```

---

## 4. Configuration Files

### 4.1 `.env` (in project root)

```
GOOGLE_API_KEY=your-api-key-here
```

### 4.2 `~/.droidrun/config.yaml` (DroidRun config)

Contains:

- LLM profiles (model settings)
- Agent settings (max_steps, etc.)
- Device connection settings

---

## 5. Known Issues & Solutions

### Issue 1: Agent Ignores `get_post_text()` Return Value

**Symptom**: Agent calls `get_post_text()` but types its own made-up text
**Root Cause**: Closure variable wasn't being captured correctly, or agent simulates tool calls
**Solution**: Use `shared_state.custom_variables.get("post_text")` in the tool function

```python
def get_post_text(*, shared_state=None, **kwargs) -> str:
    if shared_state:
        return shared_state.custom_variables.get("post_text", "")
    return ""
```

### Issue 2: LLM Transformation Returns Original Text

**Symptom**: Content transformer returns input unchanged
**Root Cause**: API key not set, or LLM error
**Solution**: Check `.env` file has `GOOGLE_API_KEY`, check logs for errors

### Issue 3: Link Crawler Using DroidAgent (Old Issue - Fixed)

**Symptom**: Crawling was slow and used device
**Root Cause**: Old code used DroidAgent for web crawling
**Solution**: Rewrote to use `requests` + `BeautifulSoup` (HTTP-based)

### Issue 4: Terminal Shows Too Much Noise

**Symptom**: Web terminal flooded with events
**Solution**: Filter to only show `💭` thoughts and `🖱️` actions in `_stream_events()`

---

## 6. Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         WEB UI (index.html)                          │
│  [Description] [Links] [Media Instructions] [Post Button]           │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      web/app.py - /api/post                          │
│                                                                      │
│  1. Extract URLs from text + links                                   │
│  2. Crawl URLs → crawled_content                                     │
│  3. Combine: description + crawled_content                           │
│  4. Transform with LLM → transformed_text                            │
│  5. Create content_dict with transformed_text                        │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    agents/threads_agent.py                           │
│                                                                      │
│  _prepare_content():                                                 │
│    - If media_instructions: skip device agent, use text directly     │
│    - Else: run agent to generate content (rarely used)               │
│                                                                      │
│  _post_to_platform():                                                │
│    - Build goal with media instructions                              │
│    - Pass variables={"post_text": full_text}                        │
│    - Run DroidAgent                                                  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     core/base_agent.py                               │
│                                                                      │
│  _run_droidrun_agent():                                              │
│    - Register get_post_text() custom tool                            │
│    - Create DroidAgent with goal, variables, custom_tools            │
│    - Stream events to web terminal                                   │
│    - Return result                                                   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      DroidRun + Android Device                       │
│                                                                      │
│  1. Execute media collection instructions                            │
│  2. Share to Threads via share sheet                                 │
│  3. Call get_post_text() → gets text from shared_state              │
│  4. Type text into composer                                          │
│  5. Publish post                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 7. API Reference

### Web Endpoints

| Endpoint        | Method | Description                     |
| --------------- | ------ | ------------------------------- |
| `/`             | GET    | Serve main web UI               |
| `/api/post`     | POST   | Post content to Threads         |
| `/api/progress` | GET    | SSE stream for progress updates |
| `/api/health`   | GET    | Health check                    |

### `/api/post` Request Body (form-data)

| Field                       | Type       | Description                                     |
| --------------------------- | ---------- | ----------------------------------------------- |
| `text`                      | string     | Description/content to post                     |
| `links`                     | string     | Newline-separated URLs to crawl                 |
| `media_source_instructions` | string     | Natural language instructions for finding media |
| `platforms`                 | JSON array | `["threads"]`                                   |

---

## 8. Dependencies

### Python Packages

```
flask
droidrun
google-genai          # NOT google-generativeai (deprecated)
python-dotenv
requests
beautifulsoup4
lxml
pyyaml
```

### External Requirements

- Android device with Portal app installed
- ADB connection to device
- `~/.droidrun/config.yaml` configured
- Google API key with Gemini access

---

## 9. Running the Project

### Start Web Server

```bash
cd /Users/anirudh/Obsidians_Droidrun
python web/app.py --port 5001
```

### Environment Variables

```bash
export GOOGLE_API_KEY="your-api-key"
# Or use .env file in project root
```

### Verify Setup

```bash
# Check DroidRun
python -c "from droidrun import DroidAgent; print('DroidRun ready')"

# Check Gemini
python -c "from google import genai; print('Gemini SDK ready')"
```

---

## 10. Debugging Tips

### Check if LLM transformation worked

Look for in terminal:

```
✨ TRANSFORMED TEXT (XXX chars):
📝 [actual transformed content]
🎯 FINAL POST TEXT (XXX chars): [content]
```

### Check if custom tool was called

Look for:

```
📋 get_post_text() called, returning XXX chars
```

### Check agent events

Look for `💭` (thoughts) and `🖱️` (actions) in web terminal

### Common Issues

1. **No GOOGLE_API_KEY**: Check `.env` file exists and has valid key
2. **Agent types wrong text**: Check `get_post_text()` is using `shared_state.custom_variables`
3. **Links not crawled**: Check `extract_urls_from_text()` finds URLs
4. **Timeout errors**: Increase timeout in ThreadsAgent (default: 120s)

---

## 11. Recent Changes History

1. **Media-First Flow**: Agent collects media BEFORE opening Threads
2. **HTTP Link Crawler**: Replaced DroidAgent-based crawler with requests+BeautifulSoup
3. **Custom Tools Fix**: Changed from closure variable to `shared_state.custom_variables.get()`
4. **Terminal Filtering**: Only show thoughts and actions, not all events
5. **LLM Prompt Improvement**: Target 400-600 chars, cleaner output
6. **Dotenv Loading**: Added automatic `.env` loading in all entry points

---

## 12. Code Patterns to Follow

### Adding a New Platform Agent

```python
class NewPlatformAgent(BasePlatformAgent):
    def __init__(self, config: DroidrunConfig, timeout: int = 60):
        super().__init__(config, "platform_name", timeout)

    async def _prepare_content(self, content, context, **kwargs):
        # Prepare content for this platform
        return {"text": ..., "hashtags": ...}

    async def _post_to_platform(self, prepared_content, media_urls=None):
        # Build goal and run agent
        goal = "..."
        result = await self._run_droidrun_agent(goal, variables={...})
        return PostResult(...)
```

### Adding a New Custom Tool

```python
def my_tool(*, shared_state=None, **kwargs) -> str:
    if shared_state:
        return shared_state.custom_variables.get("my_variable", "")
    return ""

tools = {
    "my_tool": {
        "arguments": [],  # or ["arg1", "arg2"]
        "description": "What this tool does",
        "function": my_tool
    }
}
```

---

**Document Version**: 2026-01-18
**Last Updated By**: GitHub Copilot Agent
