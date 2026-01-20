# Social Media Automation System

A production-ready web application for posting content to multiple social media platforms (Threads, Instagram, Twitter/X, LinkedIn) using intelligent content transformation and DroidRun mobile automation.

## Key Features

### Modern Web Interface

- **Real-time Progress Streaming**: Server-Sent Events (SSE) for live agent updates
- **Terminal-Style Output**: Watch agent thinking and actions in real-time
- **Multi-Platform Support**: Post to Threads, Instagram, Twitter/X, and LinkedIn
- **AI Content Transformation**: Google Gemini optimizes content per platform
- **Natural Language Media Selection**: "Gallery recent 5 images" or "Screenshots from today"
- **Link Crawling**: Automatically extracts content from provided URLs
- **Stop Button**: Abort posting workflow mid-execution
- **Responsive Design**: Dark theme with green accents

### Intelligent Automation

- **Platform-Specific Content**: AI adapts text, hashtags, and tone for each platform
- **Media Strategy Reuse**: Same media selection across platforms for consistency
- **Sequential Posting**: Posts to platforms one at a time to avoid conflicts
- **Error Handling**: Comprehensive logging and graceful failure recovery
- **Share Sheet Fallback**: Instagram Feed → Reels → plain Instagram hierarchy

## Quick Start

### Prerequisites

- Python 3.8+
- DroidRun framework installed (`pip install droidrun`)
- Android device with USB debugging enabled
- Google API key for content transformation

### Installation

1. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment**

   ```bash
   export GOOGLE_API_KEY="your-google-api-key-here"
   ```

3. **Set up DroidRun**

   ```bash
   # Copy example config
   cp config/droidrun_config.yaml.example config/droidrun_config.yaml

   # Edit config/droidrun_config.yaml and add your LLM API keys
   # See https://docs.droidrun.ai for configuration details
   ```

4. **Connect Android device**

   a. Connect phone via USB cable

   b. Enable USB debugging on phone:
   - Settings → About Phone
   - Tap "Build Number" 7 times
   - Settings → Developer Options
   - Enable "USB Debugging"

   c. Accept permission prompt on phone

   d. Run setup:

   ```bash
   droidrun setup
   ```

   e. Verify connection:

   ```bash
   droidrun ping
   ```

### Running the Application

```bash
python web/app.py
```

Open browser to `http://localhost:5001`

## Usage

### Web Interface Workflow

1. **Write Description** (optional)
   - Your main post content
   - Will be transformed for each platform

2. **Add Media Instructions** (optional)
   - Natural language: "Gallery recent 5 images"
   - Examples: "Screenshots from today", "Media from last 2 days"

3. **Add Links** (optional)
   - One URL per line
   - Content will be crawled and incorporated

4. **Select Platforms** (required)
   - Choose: Threads, Instagram, Twitter/X, LinkedIn
   - Must select at least one

5. **Click "Post Now"**
   - Watch real-time progress
   - Results appear for each platform
   - Use "Stop" to abort if needed

### Natural Language Media Examples

```
Gallery recent images
All media between Jan 4 and Jan 6
Media from last 2 days
All videos from gallery
Screenshots from today
Content uploaded in the last 48 hours
```

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Web Interface                          │
│                 (Flask + SSE Progress)                    │
├──────────────────────────────────────────────────────────┤
│                                                            │
│  Content Input      Link Crawler      Platform Agents    │
│  ├─ Description     ├─ URL Extract    ├─ Threads         │
│  ├─ Media Hints     ├─ Context        ├─ Instagram       │
│  └─ Links           └─ AI Transform   ├─ Twitter/X       │
│                                        └─ LinkedIn        │
└──────────────────────────────────────────────────────────┘
```

## Platform Agents

### Threads

- Conversational, community-oriented content
- Thread support (multi-post style)
- Natural tone and hashtags
- 500 character limit per post

### Instagram

- Visual, engaging content with captions
- Share sheet selection (Feed → Reels → Instagram fallback)
- Catchy captions (150-200 chars)
- 20+ relevant hashtags
- Emoji suggestions

### Twitter/X

- Concise, viral-ready content
- 280 character optimization
- Trending hashtags
- Media attachment via Google Photos

### LinkedIn

- Professional, technical content
- Technical headlines and detailed descriptions
- 15 professional hashtags
- Thought leadership tone

## Project Structure

```
.
├── web/
│   ├── app.py                 # Flask server with SSE
│   ├── templates/
│   │   └── index.html        # Web UI
│   └── static/
│       ├── style.css         # Dark theme styling
│       └── app.js            # Frontend + SSE client
├── agents/
│   ├── threads_agent.py      # Threads posting logic
│   ├── instagram_agent.py    # Instagram automation
│   ├── twitter_agent.py      # Twitter/X posting
│   └── linkedin_agent.py     # LinkedIn posting
├── core/
│   ├── models.py             # Data models
│   ├── base_agent.py         # Abstract base agent
│   ├── link_crawler.py       # URL crawling
│   ├── content_transformer.py # AI optimization
│   └── orchestrator.py       # Legacy CLI orchestrator
├── config/
│   ├── settings.py           # App configuration
│   └── droidrun_config.yaml  # DroidRun settings
├── utils/
│   ├── logger.py             # Logging utilities
│   └── text_utils.py         # Text processing
└── requirements.txt          # Dependencies
```

## How It Works

### Content Transformation Flow

```
User Input (description + links + media)
    ↓
Extract URLs from description and links field
    ↓
Crawl URLs for content (2-level deep)
    ↓
Combine user description + crawled content
    ↓
AI Transformation (Google Gemini per platform)
    ↓
Platform-specific optimized content
    ↓
Sequential posting to selected platforms
    ↓
Real-time progress streamed to browser
```

### Media Selection Strategy

1. **First Platform**: Agent navigates device to select media based on instructions
2. **Subsequent Platforms**: Reuses same media selection strategy
3. **Share Sheet Handling**:
   - Instagram: Feed → Reels → Instagram fallback with waits
   - LinkedIn: Explicit media instruction parsing
   - Twitter/X: Direct share to Twitter
   - Threads: Direct share to Threads

## Configuration

### Environment Variables

```bash
# Required
export GOOGLE_API_KEY="your-google-api-key"

# Optional
export APP_ENV="production"  # development, production, testing
export LOG_LEVEL="INFO"      # DEBUG, INFO, WARNING, ERROR
```

### DroidRun Configuration

Edit `config/droidrun_config.yaml`:

```yaml
llm_profiles:
  default:
    provider: "openai" # or anthropic, google
    model: "gpt-4"
    api_key: "your-api-key"

agent:
  max_steps: 15
  timeout: 1500 # seconds
```

### Platform Settings

Edit `config/settings.py` to enable/disable platforms:

```python
PLATFORMS = {
    "threads": {"enabled": True, "timeout": 60},
    "instagram": {"enabled": True, "timeout": 90},
    "twitter": {"enabled": True, "timeout": 60},
    "linkedin": {"enabled": True, "timeout": 90},
}
```

## API Endpoints

### POST `/api/post`

Submit content for posting.

**Form Data:**

- `text`: Post description
- `media_source_instructions`: Natural language media selection
- `links`: URLs (one per line)
- `platforms`: JSON array `["threads", "instagram"]`

**Response:**

```json
{
  "success": true,
  "message": "Content posted successfully",
  "results": [{ "platform": "threads", "success": true, "reason": "Posted" }]
}
```

### GET `/api/progress`

Server-Sent Events stream for real-time updates.

**Event Data:**

```json
{
  "step": 1,
  "total": 3,
  "message": "Preparing content",
  "percentage": 33,
  "log": "Starting transformation...",
  "logType": "info"
}
```

## Troubleshooting

### Common Issues

**GOOGLE_API_KEY not set**

- Set environment: `export GOOGLE_API_KEY="your-key"`
- Or create `.env` file in project root

**config/droidrun_config.yaml not found**

- Copy `config/droidrun_config.yaml.example`
- Add your LLM API keys
- Verify YAML syntax

**Platform posting fails**

- Check app is installed on device
- Verify account is logged in
- Review logs for specific errors

**Media selection fails**

- Ensure instructions are clear
- Check Google Photos app is installed
- Verify device has media in specified timeframe

**Progress stream disconnects**

- Check browser console for errors
- Verify Flask server is running
- Check network connectivity

### Debug Mode

```bash
LOG_LEVEL=DEBUG python web/app.py
```

Shows:

- Detailed agent decision-making
- Full error stack traces
- URL extraction details
- Content transformation steps

## Performance

- **Link Crawling**: 5-10s per URL
- **Content Transformation**: 3-5s per platform
- **Platform Posting**: 20-60s per platform
- **Total Workflow**: 1-4 minutes for 4 platforms with media

## License

Project by Umang Khhatri

## Support

For issues:

1. Check troubleshooting section
2. Review terminal logs
3. Check DroidRun documentation at https://docs.droidrun.ai
4. Review code comments for agent-specific details
