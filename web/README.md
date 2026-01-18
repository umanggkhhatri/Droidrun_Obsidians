# Social Media Automator - Web Interface

A simple web-based interface for uploading content and automatically posting to multiple social media platforms (Twitter, Threads, Instagram, LinkedIn).

## Features

- 📸 Upload media files (images and videos)
- ✍️ Write description/caption
- 🔗 Add multiple links
- 📱 Select target platforms
- 🚀 Post to all platforms with one click
- 📊 View results for each platform

## Setup

### Prerequisites

- Python 3.8+
- Flask
- Droidrun (for device automation)

### Installation

1. Install Python dependencies:

```bash
pip install flask
```

2. Ensure the main Droidrun system is set up (see parent README.md)

## Running the Web Server

```bash
cd /Users/anirudh/Droidrun_Obsidians/web
python app.py
```

The server will start on `http://localhost:5000`

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
- `links` (string): Links (one per line)
- `media` (files): Media files (images/videos)
- `platforms` (JSON array): Selected platforms ["twitter", "threads", "instagram", "linkedin"]

**Response:**

```json
{
  "success": true,
  "message": "Content posted successfully",
  "results": [
    {
      "platform": "twitter",
      "success": true,
      "reason": "Posted successfully"
    }
  ]
}
```

## File Structure

```
web/
├── app.py                 # Flask server
├── templates/
│   └── index.html        # Main web interface
└── static/
    ├── style.css         # Styling
    └── app.js            # Frontend logic
```

## Supported Platforms

- **Twitter (X)**: 280 character posts
- **Threads**: 500 character posts
- **Instagram**: 2200 character captions
- **LinkedIn**: 3000 character posts

## Supported Media Types

- Images: PNG, JPG, JPEG, GIF
- Videos: MP4, MOV, WebM

## Troubleshooting

**Port 5000 already in use:**

```bash
lsof -i :5000
kill -9 <PID>
```

**File upload errors:**

- Check `/tmp/web_uploads` directory permissions
- Ensure media files are in supported formats
- Check file size (max 50MB)

**Posting fails:**

- Ensure Droidrun is properly configured
- Check device is connected via ADB
- Verify `~/.droidrun/config.yaml` exists

## Development

To enable debug mode and auto-reload:

```python
app.run(debug=True)
```

(Already enabled in app.py)

## Production Notes

For production deployment:

1. Set `debug=False` in `app.py`
2. Use a production WSGI server (Gunicorn/uWSGI)
3. Set proper CORS headers if serving from different domain
4. Configure proper upload directory with cleanup
5. Add authentication/rate limiting as needed

Example with Gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```
