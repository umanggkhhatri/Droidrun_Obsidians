# Web Interface Architecture - Complete Guide

## Summary of Changes Made

The web interface has been completely refactored from a **file upload-based system** to a **natural language media instruction system** that works with Droidrun's device automation capabilities.

## Frontend Structure

### HTML Form Fields (in order)

1. **Description** (Optional)
   - Textarea: `#descriptionInput`
   - Max: 5000 characters
   - Purpose: Main post content
   - Placeholder shows character count

2. **Media Source** (Optional)
   - Textarea: `#mediaSourceInput`
   - Purpose: Natural language instructions for device media collection
   - Examples provided:
     - "Gallery recent 5 images"
     - "All media between Jan 4 and Jan 6"
     - "Media from last 2 days"
     - "WhatsApp chat with +91XXXXXXXXXX (last 10 messages)"
     - "All videos from gallery"
     - "Screenshots from today"

3. **Links** (Optional)
   - Textarea: `#linksInput`
   - Format: One link per line
   - Purpose: URLs to include in post

4. **Platform Selection** (Required)
   - Currently: Only Threads available
   - Checkbox: `input[name="platform"][value="threads"]`
   - Locked to Threads only (Twitter/Instagram/LinkedIn removed)

5. **Action Buttons**
   - "🚀 Post to Threads" - Submits form
   - "🗑️ Clear All" - Resets all fields

### Removed Components

- ❌ File upload area (drag-drop zone)
- ❌ File input element
- ❌ File list display
- ❌ All file handling logic

## Backend Processing

### Flask Endpoint: `/api/post`

**Input:** Form data

```python
{
    "text": "User's description",
    "media_source_instructions": "Gallery recent 5 images",
    "links": "https://example.com\nhttps://another.com",
    "platforms": '["threads"]'
}
```

**Processing:**

1. Extract all form fields
2. Validate: At least one of (text, media_source_instructions, links) required
3. Parse platforms JSON
4. Create Content object with media instructions in context_data
5. Pass to ThreadsAgent

**Output:** JSON response

```json
{
  "success": true,
  "message": "Content posted successfully",
  "results": [
    {
      "platform": "threads",
      "success": true,
      "reason": "Post published successfully"
    }
  ]
}
```

## Agent Processing

### ThreadsAgent Flow

1. **Content Preparation** (\_prepare_content method)
   - Receives content dict with media_source_instructions in context
   - Extracts media instructions from context
   - Passes through to prepared content dict

2. **Platform Posting** (\_post_to_platform method)
   - Retrieves media_source_instructions from prepared_content
   - Constructs agent goal with:
     - Main post text
     - Hashtags
     - Media collection instruction (from natural language)
     - Thread content (if applicable)

3. **Agent Goal Example**
   ```
   Post to Threads:
   1. Open the Threads app
   2. Tap the compose icon to create a new post
   3. Add the following text: [post text]
   4. Media attachment: Collect media using: Gallery recent 5 images
      Then attach collected media to the post.
   5. If thread items provided, create a thread...
   6. Publish the post
   ```

## Real-time Progress Tracking

### SSE Endpoint: `/api/progress`

The server continuously emits progress events:

```json
{
  "step": 1,
  "total": 3,
  "message": "🔄 Preparing content",
  "details": "Media Source: Gallery recent 5 images",
  "percentage": 33
}
```

Progress stages:

1. Preparation (0%)
2. ThreadsAgent initialization (33%)
3. Posting to platform (66%)
4. Completion (100%)

## Validation Rules

**Form Submission Requires:**

- ✅ At least ONE of:
  - Description text (any length > 0)
  - Media source instructions (any length > 0)
  - Links (any length > 0)

- ✅ At least one platform selected (currently: Threads only, always checked)

**Frontend Validation:**

- Alerts user if validation fails before sending to server
- Prevents empty submissions

**Backend Validation:**

- Additional server-side validation
- Returns 400 error with message if invalid
- Returns 500 error if config not loaded

## State Management (JavaScript)

```javascript
const state = {
  description: "", // From descriptionInput
  mediaSourceInstructions: "", // From mediaSourceInput
  links: "", // From linksInput
  platforms: ["threads"], // Always ["threads"]
  eventSource: null, // For SSE connection
};
```

## Security & Performance

### Upload Folder

- **Location:** `/tmp/web_uploads`
- **Max Size:** 50MB total request size
- **Note:** No longer used since we're not uploading files

### Config Loading

- **Location:** `~/.droidrun/config.yaml`
- **Required:** Yes, startup will fail if missing
- **Fallback:** None (intentional - config must exist)

## Error Handling

**Client-side:**

- Validation errors: Alert user with specific message
- Network errors: Display error in results section
- Progress stream disconnection: Handled gracefully

**Server-side:**

- Invalid JSON in platforms: Defaults to empty array → validation fails
- Missing config: Returns 500 error
- Agent error: Caught and returned in results
- Timeout: 120 second limit per platform

## Complete Form Submission Flow

```
User fills form
    ↓
User clicks "Post to Threads"
    ↓
JavaScript validation (client-side)
    ↓
Show loading overlay + connect to SSE stream
    ↓
Collect form data + create FormData object
    ↓
POST /api/post with FormData
    ↓
Flask endpoint processes request
    ↓
Server-side validation
    ↓
ThreadsAgent.prepare_and_post() called
    ↓
Agent receives media instructions in goal
    ↓
Droidrun agent automates device
    ↓
Results collected + returned
    ↓
Display results to user
    ↓
Clear form (on success)
```

## Testing Checklist

- [ ] Start Flask server without errors
- [ ] Load web interface in browser
- [ ] Media source instructions field visible
- [ ] No file upload area visible
- [ ] Validation: Can't submit empty form
- [ ] Validation: Can submit with just media instructions
- [ ] Validation: Can submit with description + media instructions + links
- [ ] Progress stream shows media instructions in details
- [ ] Results display success/failure
- [ ] Clear button resets all fields
- [ ] Config file (~/.droidrun/config.yaml) being read on startup

## Common Issues

**Issue:** Empty form submitted
**Solution:** Client-side validation alerts user; server-side validation returns 400

**Issue:** Config not found
**Solution:** Server fails to start with clear error message pointing to ~/.droidrun/config.yaml

**Issue:** Media instructions not shown in progress
**Solution:** Check emit_progress() call in web/app.py line 236

**Issue:** Agent not receiving instructions
**Solution:** Verify media_source_instructions passed through context → prepared_content → goal

## Files Modified

1. ✅ `web/templates/index.html` - Removed file upload, added media source field
2. ✅ `web/static/app.js` - Removed file handling, added media instructions support
3. ✅ `web/static/style.css` - No changes needed (upload styles harmless)
4. ✅ `web/app.py` - Removed file upload handling, added media instructions
5. ✅ `agents/threads_agent.py` - Updated to handle media source instructions
6. ✅ `core/base_agent.py` - No changes (already flexible)

## Next Steps

1. Test the complete flow with a device connected
2. Verify agent receives and processes media instructions
3. Monitor device for media collection behavior
4. Debug any issues with natural language interpretation
