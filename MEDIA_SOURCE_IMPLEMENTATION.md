# Media Source Instructions Implementation

## Overview

Replaced direct file uploads with natural language media collection instructions. The agent now receives instructions on how to locate media on the device, rather than pre-uploaded files.

## Architecture Changes

### 1. Web Interface (HTML/CSS/JS)

**File: `web/templates/index.html`**

- ❌ Removed: File upload area (`uploadArea` div with drag-drop functionality)
- ✅ Added: Media Source Instructions textarea with helpful examples
  - Examples: "Gallery recent 5 images", "All media between Jan 4 and Jan 6", etc.

**File: `web/static/app.js`**

- ❌ Removed: All file handling logic
  - `handleDragOver()`, `handleDragLeave()`, `handleDrop()`, `handleFileSelect()`
  - `addFiles()`, `isAllowedFile()`, `updateFileList()`, `removeFile()`
- ✅ Added: `handleMediaSourceChange()` to capture media source instructions
- ✅ Updated: Form submission to include `media_source_instructions` field
- ✅ Updated: Validation to require either text, media instructions, OR links

### 2. Flask Backend

**File: `web/app.py`**

- ❌ Removed: Media file handling (`'media' in request.files`)
- ✅ Added: `media_source_instructions` form field extraction
- ✅ Updated: Content object creation to include media source instructions
- ✅ Updated: Content dict with `media_source_instructions` instead of media files
- ✅ Enhanced: Progress reporting to show media source instructions when provided

### 3. ThreadsAgent

**File: `agents/threads_agent.py`**

- ✅ Updated: `_prepare_content()` to pass through `media_source_instructions` from context
- ✅ Updated: `_post_to_platform()` to handle media source instructions
  - If instructions provided: "Collect media using: [instructions]"
  - If no instructions: "No media to upload"
- ✅ Enhanced: Goal construction to include media collection instructions for the agent

## Data Flow

```
User Input
    ↓
HTML Form (mediaSourceInput)
    ↓
JavaScript (mediaSourceInstructions in state)
    ↓
FormData.append("media_source_instructions", ...)
    ↓
Flask /api/post endpoint
    ↓
Extract: media_source_instructions from request.form
    ↓
Content object (in context_data and metadata)
    ↓
ThreadsAgent._prepare_content()
    ↓
ThreadsAgent._post_to_platform()
    ↓
Agent goal includes: "Collect media using: [natural language instructions]"
    ↓
Droidrun agent automates device to find media
    ↓
Post to Threads with collected media
```

## Usage Examples

Users can now provide natural language instructions like:

1. **Gallery-based:**
   - "Gallery recent 5 images"
   - "All photos from last 2 days"
   - "Recent videos"

2. **Date-based:**
   - "All media between Jan 4 and Jan 6"
   - "Media from today"
   - "Content uploaded in last 48 hours"

3. **App-specific:**
   - "WhatsApp chat with +91XXXXXXXXXX (last 10 messages)"
   - "Messages from group 'College Friends' with attachments"
   - "Screenshots from today"

4. **Combined:**
   - "Recent photos and videos from the last week"
   - "All media collected on device in the past 24 hours"

## Benefits

✅ **Device-native media:** Media originates from device, ensuring compatibility with agent automation  
✅ **Natural language:** Users describe where to find media in plain English  
✅ **Flexible:** Supports any media location (Gallery, WhatsApp, Downloads, etc.)  
✅ **AI-powered:** Agent understands instructions and navigates device accordingly  
✅ **No file uploads:** Eliminates server storage and bandwidth issues

## Field Validation

- **Required:** At least ONE of the following must be provided:
  - Description text
  - Media source instructions
  - Links
- **Optional:** Any combination of the above
- **Empty:** Media source field is completely optional

## Testing

To test this implementation:

1. Start the Flask server: `python web/app.py`
2. Open web interface at `http://localhost:5000`
3. Enter a description (optional)
4. Enter media source instructions (e.g., "Gallery recent 5 images")
5. Enter links if desired (optional)
6. Click "Post to Threads"
7. Monitor progress via SSE stream
8. View results

The agent will:

1. Process the description and media instructions
2. Navigate to device Gallery using natural language instruction
3. Collect the specified media
4. Compose post with text
5. Attach collected media
6. Post to Threads
