# Social Media Automator - Web Interface

A modern web-based interface for posting content to multiple social media platforms (Threads, Instagram, Twitter/X, LinkedIn) with real-time progress tracking and natural language media selection.

## ✨ Features

- 📝 **Rich Text Input**: Write descriptions up to 5000 characters
- 📱 **Natural Language Media**: "Gallery recent 5 images" instead of file uploads
- 🔗 **Link Crawling**: Automatic URL extraction and content enrichment
- 🚀 **Multi-Platform Posting**: Threads, Instagram, Twitter/X, LinkedIn
- 📊 **Real-Time Progress**: Server-Sent Events stream agent logs to browser
- 🎨 **Modern UI**: Dark theme with green accents, responsive design
- ⏹️ **Stop Button**: Abort workflow mid-execution
- ✅ **Platform Validation**: Enforces at least one platform selected
- 🔄 **Media Strategy Reuse**: Same media across all platforms

## Setup

### Prerequisites

- Python 3.14+
- Flask
- DroidRun framework
- Google API key (for content transformation)
- Android device with ADB enabled

### Installation

1. Install Python dependencies:

```bash
pip install flask google-generativeai beautifulsoup4 requests
```

2. Set up environment variable:

```bash
export GOOGLE_API_KEY="your-google-api-key-here"
```

3. Create `config/droidrun_config.yaml` with LLM profiles

4. Ensure DroidRun system is set up (see parent README.md)

## Running the Web Server

```bash
cd web
python app.py
```

The server will start on `http://localhost:5001`

## Usage

1. **Open browser** to `http://localhost:5001`

2. **Fill in the form**:
   - Description (optional): Main post text
   - Media Source (optional): Natural language like "Gallery recent 5 images"
   - Links (optional): One URL per line
   - Platforms (required): Select at least one

3. **Click "Post Now"**:
   - Watch real-time progress in terminal on right
   - See agent actions and decisions
   - View results for each platform

4. **Stop if needed**:
   - Button changes to "Stop" during posting
   - Click to abort workflow
   - All inputs disabled during posting

## Media Instruction Examples

```
Gallery recent 5 images
All media between Jan 4 and Jan 6
Media from last 2 days
WhatsApp chat with +91XXXXXXXXXX (last 10 messages)
All videos from gallery
Screenshots from today
Content uploaded to device in the last 48 hours
```

## API Endpoints

### GET `/`

Serves the main web interface.

### GET `/api/health`

Health check endpoint.

```json
{
  "status": "ok",
  "message": "Server is running"
}
```

### POST `/api/post`

Main endpoint to post content to platforms.

**Form Data:**

- `text` (string): Post description/caption
- `media_source_instructions` (string): Natural language media selection
- `links` (string): Links (one per line)
- `platforms` (JSON array): Selected platforms `["threads", "instagram", "twitter", "linkedin"]`

**Response:**

```json
{
  "success": true,
  "message": "Content posted successfully",
  "results": [
    {
      "platform": "threads",
      "success": true,
      "reason": "Post published successfully",
      "error": null
    }
  ]
}
```

### GET `/api/progress`

Server-Sent Events (SSE) stream for real-time progress updates.

**Event Data:**

```json
{
  "step": 1,
  "total": 3,
  "message": "🔄 Preparing content",
  "details": "Media Source: Gallery recent 5 images",
  "percentage": 33,
  "log": "Starting content preparation...",
  "log_type": "info"
}
```

## File Structure

```
web/
├── app.py                 # Flask server with SSE support
├── README.md             # This file
├── templates/
│   └── index.html        # Main web UI (two-column layout)
└── static/
    ├── style.css         # Dark theme with green accents
    └── app.js            # Frontend logic + EventSource SSE
```

## Supported Platforms

- **Threads**: 500 character posts
- **Instagram**: 2200 character captions with share sheet fallback
- **Twitter/X**: 280 character posts
- **LinkedIn**: 3000 character posts with media instruction parsing

## UI Features

- **Two-Column Layout**: Main form on left, terminal output on right
- **Dark Theme**: Zinc/slate colors with green accent (#22c55e)
- **Platform Selector**: 4 buttons in single line with Font Awesome icons
- **Terminal Output**: Real-time agent logs with color coding
- **Progress Bar**: Shows completion percentage
- **Stop Button**: Changes from "Post Now" to red "Stop" during execution
- **Input Disabling**: All form controls disabled during posting (except Stop)
- **Platform Validation**: Must select at least one, can't deselect last one

## Troubleshooting

**Port already in use:**

```bash
lsof -ti:5001 | xargs kill -9
```

**GOOGLE_API_KEY Error:**

```bash
export GOOGLE_API_KEY="your-api-key"
```

**Config.yaml Not Found:**

```bash
mkdir -p ~/.droidrun
# Create config.yaml with LLM profiles
```

**Progress Stream Disconnects:**

- Check browser console
- Verify Flask server running
- Refresh the page

**Platform Posting Fails:**

- Verify app installed on device
- Check account logged in
- Review terminal logs

## Development

Debug mode:

```bash
LOG_LEVEL=DEBUG python app.py
```

## Production Notes

Use production WSGI server:

```bash
gunicorn -w 4 -b 0.0.0.0:5001 app:app --timeout 300
```

1. Set `debug=False` in `app.py`
2. Use a production WSGI server (Gunicorn/uWSGI)
3. Set proper CORS headers if serving from different domain
4. Configure proper upload directory with cleanup
5. Add authentication/rate limiting as needed

Example with Gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```
