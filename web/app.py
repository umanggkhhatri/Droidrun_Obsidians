"""
Social Media Automator Web Interface
Flask server for uploading content and posting to social platforms
"""

import os
import sys
import json
import yaml
import asyncio
import queue
from pathlib import Path
from flask import Flask, render_template, request, jsonify, Response
from werkzeug.utils import secure_filename

# Load .env file if present (for GOOGLE_API_KEY etc.)
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("SUCCESS: Loaded .env file")
except ImportError:
    print("WARNING: python-dotenv not installed, using system environment variables")

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from droidrun import DroidrunConfig
from config.settings import get_config
from core.models import Content
from agents import ThreadsAgent, InstagramAgent, TwitterAgent, LinkedInAgent
from core.link_crawler import LinkCrawler, extract_urls_from_text
from core.base_agent import set_log_callback
from core.content_transformer import transform_content_with_llm

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max
app.config['UPLOAD_FOLDER'] = '/tmp/web_uploads'
# Disable static asset caching in dev to avoid noisy 304s
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0


@app.after_request
def add_no_cache_headers(response):
    """Reduce 304s by disabling cache for static assets (dev convenience)."""
    if request.path.startswith('/static/') or request.path == '/':
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Load project config from config/droidrun_config.yaml
config_path = os.path.join(Path(__file__).parent.parent, 'config', 'droidrun_config.yaml')
print(f"\n{'='*60}")
print(f"CONFIGURATION LOADING")
print(f"{'='*60}")

if not os.path.exists(config_path):
    print(f"ERROR: CRITICAL ERROR: config/droidrun_config.yaml NOT FOUND at {config_path}")
    print(f"   Please create this file first!")
    sys.exit(1)

# Load and parse the config file
try:
    with open(config_path, 'r') as f:
        droidrun_config_data = yaml.safe_load(f)
    print(f"SUCCESS: config/droidrun_config.yaml loaded successfully")
    print(f"   Location: {config_path}")
    print(f"   LLM Profiles: {list(droidrun_config_data.get('llm_profiles', {}).keys())}")
except Exception as e:
    print(f"ERROR: FAILED to parse config/droidrun_config.yaml: {e}")
    sys.exit(1)

# Initialize DroidrunConfig with the loaded YAML data
try:
    # Parse the max_steps from config
    max_steps = droidrun_config_data.get('agent', {}).get('max_steps', 15)
    
    # Create DroidrunConfig and pass the loaded configuration
    droidrun_config = DroidrunConfig.from_yaml(config_path)
    print(f"SUCCESS: DroidrunConfig initialized with max_steps: {max_steps}")
    print(f"   Agent config: {droidrun_config_data.get('agent', {})}")
    
except TypeError:
    # If DroidrunConfig doesn't accept kwargs, try creating it normally
    # but set max_steps attribute directly
    try:
        droidrun_config = DroidrunConfig()
        # Try to set max_steps attribute
        if hasattr(droidrun_config, 'agent'):
            if hasattr(droidrun_config.agent, 'max_steps'):
                droidrun_config.agent.max_steps = droidrun_config_data.get('agent', {}).get('max_steps', 15)
        print(f"SUCCESS: DroidrunConfig initialized (fallback method)")
    except Exception as e2:
        print(f"ERROR: CRITICAL: Failed to initialize DroidrunConfig: {e2}")
        droidrun_config = None
except Exception as e:
    print(f"ERROR: CRITICAL: Error initializing DroidrunConfig: {e}")
    print(f"   This means config/droidrun_config.yaml is not being used!")
    droidrun_config = None

# Load app config
app_config = get_config()
print(f"SUCCESS: App config loaded: {app_config.__class__.__name__}")
print(f"   MAX_CRAWL_DEPTH: {app_config.MAX_CRAWL_DEPTH}")
enabled_platforms = [k for k, v in app_config.PLATFORMS.items() if v.get('enabled')]
print(f"   Enabled platforms: {enabled_platforms}")

# Check for GOOGLE_API_KEY (required for content transformation)
google_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if google_api_key:
    masked = google_api_key[:8] + "..." + google_api_key[-4:] if len(google_api_key) > 12 else "***"
    print(f"SUCCESS: GOOGLE_API_KEY found: {masked}")
else:
    print(f"WARNING: GOOGLE_API_KEY not set! Content transformation will fail.")
    print(f"   Set it with: export GOOGLE_API_KEY='your-api-key-here'")
    print(f"   Or add it to a .env file in the project root.")

print(f"{'='*60}\n")


# Progress queue for streaming updates
progress_queue = queue.Queue()

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'webm'}


def _strip_emoji(text: str) -> str:
    """Remove emojis and non-ASCII characters for cleaner UI logs."""
    try:
        return (text or "").encode('ascii', 'ignore').decode()
    except Exception:
        return text or ""


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def emit_progress(step, total, message, details='', log=None, log_type='info'):
    """Emit a progress update to the queue"""
    progress_queue.put({
        'step': step,
        'total': total,
        'message': _strip_emoji(message),
        'details': _strip_emoji(details),
        'percentage': int((step / total) * 100) if total > 0 else 0,
        'log': _strip_emoji(log) if isinstance(log, str) else log,
        'logType': log_type
    })


def emit_log(message, log_type='info'):
    """Emit a log-only update to the queue"""
    progress_queue.put({
        'type': 'log',
        'log': _strip_emoji(message),
        'logType': log_type
    })


@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')


@app.route('/api/progress', methods=['GET'])
def get_progress():
    """Server-Sent Events endpoint for progress updates"""
    def generate():
        while True:
            try:
                # Get progress from queue (timeout after 30 seconds)
                progress = progress_queue.get(timeout=30)
                yield f"data: {json.dumps(progress)}\n\n"
            except queue.Empty:
                # Send heartbeat to keep connection alive
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
            except GeneratorExit:
                break
    
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'Server is running'})


@app.route('/api/post', methods=['POST'])
def post_content():
    """
    Main endpoint to post content to platforms
    Expects: text, media_source_instructions, links, and platforms selection
    """
    try:
        # Extract form data
        text = request.form.get('text', '').strip()
        media_source_instructions = request.form.get('media_source_instructions', '').strip()
        links = request.form.get('links', '').strip()
        platforms_json = request.form.get('platforms', '[]')
        
        # Parse platforms
        try:
            platforms_raw = json.loads(platforms_json)
            emit_log(f'RAW platform data received: {platforms_raw} (type: {type(platforms_raw)})', 'info')
            
            # Normalize platform names (lowercase, strip whitespace)
            platforms = [p.lower().strip() for p in platforms_raw if p]
            emit_log(f'Normalized platforms: {platforms}', 'info')
        except (json.JSONDecodeError, TypeError) as e:
            emit_log(f'ERROR: Error parsing platforms JSON: {e}', 'error')
            platforms = []
        
        # Validate platform names against supported set
        valid_platform_names = {'twitter', 'threads', 'instagram', 'linkedin'}
        invalid_platforms = [p for p in platforms if p not in valid_platform_names]
        if invalid_platforms:
            emit_log(f'WARNING: Invalid platform names detected: {invalid_platforms}', 'warning')
            platforms = [p for p in platforms if p in valid_platform_names]
        
        # Log final validated platforms
        emit_log(f'SUCCESS: VALIDATED platform selection: {platforms}', 'step')
        emit_log(f'   Count: {len(platforms)} platform(s)', 'info')
        
        # Validation: require at least text, media instructions, or links
        if not text and not media_source_instructions and not links:
            return jsonify({
                'success': False,
                'message': 'Please provide text, media source instructions, or links'
            }), 400
        
        if not platforms:
            return jsonify({
                'success': False,
                'message': 'Please select at least one platform'
            }), 400
        
        # Log and validate platform selection
        emit_log(f'SUCCESS: Platform selection validated: {platforms}', 'step')
        
        # === STEP 1: CRAWL LINKS FIRST ===
        crawled_content = ""
        all_urls = []
        
        # Extract URLs from text field
        if text:
            urls_in_text = extract_urls_from_text(text)
            all_urls.extend(urls_in_text)
            emit_log(f'Found {len(urls_in_text)} URLs in description', 'info')
        
        # Extract URLs from links field
        if links:
            link_lines = [l.strip() for l in links.split('\n') if l.strip()]
            for line in link_lines:
                urls_in_line = extract_urls_from_text(line)
                all_urls.extend(urls_in_line)
            emit_log(f'Found {len(link_lines)} links in links field', 'info')
        
        # Remove duplicates
        all_urls = list(set(all_urls))
        
        # Crawl all URLs
        if all_urls:
            emit_log(f'Crawling {len(all_urls)} unique URLs...', 'step')
            
            crawler = LinkCrawler(max_links_per_page=5, timeout=15)
            
            for url in all_urls[:3]:  # Limit to 3 URLs max
                try:
                    emit_log(f'Crawling: {url}', 'info')
                    content_from_url = crawler.crawl_url(url)
                    if content_from_url:
                        crawled_content += f"\n\n{content_from_url}"
                        emit_log(f'SUCCESS: Crawled {len(content_from_url)} chars from {url}', 'success')
                except Exception as e:
                    emit_log(f'WARNING: Failed to crawl {url}: {str(e)}', 'error')
        
        # === STEP 2: COMBINE DESCRIPTION + CRAWLED CONTENT ===
        combined_content = ""
        
        if text:
            combined_content = f"USER DESCRIPTION:\n{text}"
        
        if crawled_content:
            combined_content += f"\n\nCRAWLED LINK CONTENT:{crawled_content}"
            emit_log(f'Combined content: {len(combined_content)} total chars', 'info')
        
        # === STEP 3: TRANSFORM COMBINED CONTENT WITH LLM (PLATFORM-SPECIFIC) ===
        if combined_content and len(combined_content) > 10:
            try:
                # Transform content separately for each platform for better results
                emit_log(f'Transforming content for {len(platforms)} platforms ({len(combined_content)} chars)...', 'step')
                emit_log(f'Input preview: {combined_content[:300]}...', 'info')
                
                # For now, transform once with general platform or first selected platform
                # TODO: Consider transforming separately per platform in future
                primary_platform = platforms[0] if platforms else "general"
                emit_log(f'Using {primary_platform} tone and style', 'info')
                
                # Run async transformation in thread to avoid event loop issues
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        transform_content_with_llm(combined_content, droidrun_config, platform=primary_platform)
                    )
                    transformed_text = future.result(timeout=90)  # 90s timeout for larger content with crawling
                
                if transformed_text and len(transformed_text) > 20:
                    emit_log(f'SUCCESS: TRANSFORMED TEXT ({len(transformed_text)} chars):', 'success')
                    emit_log(f'{transformed_text}', 'success')
                    text = transformed_text  # Use transformed text for posting
                else:
                    emit_log(f'WARNING: LLM returned empty or too short, using original text', 'info')
                    text = text if text else "Check out this content!"
            except Exception as e:
                emit_log(f'ERROR: LLM transformation error: {type(e).__name__}: {str(e)}', 'error')
                emit_log(f'WARNING: Using original text instead', 'info')
                # Continue with original text if transformation fails
        elif not text:
            text = "Check out this content!"
            emit_log(f'WARNING: No text content, using default', 'info')
        
        # Log the final text that will be posted
        emit_log(f'FINAL POST TEXT ({len(text)} chars): {text}', 'step')
        
        # Create content object with media source instructions
        # Note: 'text' variable now contains the LLM-transformed text
        content = Content(
            original_text=text,  # This is the transformed text now
            extracted_urls=all_urls,  # Use the URLs we already extracted
            media_files=[],
            video_files=[],
            context_data={
                'media_source_instructions': media_source_instructions
            },
            metadata={
                'media_source_instructions': media_source_instructions
            }
        )
        
        # Prepare content dict for agents with media instructions
        # Use the transformed 'text' variable directly (not content.original_text)
        content_dict = {
            "text": text,  # Use transformed text variable
            "media_source_instructions": media_source_instructions,
            "urls": content.extracted_urls,
        }
        
        emit_log(f'Content package prepared for agents:', 'info')
        emit_log(f'  - Text ({len(text)} chars): {text[:100]}...', 'info')
        emit_log(f'  - Media instructions: {media_source_instructions[:60] if media_source_instructions else "None"}', 'info')
        emit_log(f'  - URLs: {len(content.extracted_urls)} collected', 'info')
        
        # Post to platforms
        if not droidrun_config:
            return jsonify({
                'success': False,
                'message': 'Droidrun config not loaded. Ensure config/droidrun_config.yaml exists'
            }), 500
        
        # Build agents_map only for selected platforms
        agents_map = {}
        
        # Initialize agents only for user-selected platforms
        if 'threads' in platforms:
            agents_map['threads'] = ThreadsAgent(droidrun_config, timeout=1500)
            emit_log(f'SUCCESS: Initialized Threads agent (timeout: 1500s)', 'info')
        
        if 'instagram' in platforms:
            agents_map['instagram'] = InstagramAgent(droidrun_config, timeout=1500)
            emit_log(f'SUCCESS: Initialized Instagram agent (timeout: 1500s)', 'info')
        
        if 'twitter' in platforms:
            agents_map['twitter'] = TwitterAgent(droidrun_config, timeout=1500)
            emit_log(f'SUCCESS: Initialized Twitter/X agent (timeout: 1500s)', 'info')
        
        if 'linkedin' in platforms:
            agents_map['linkedin'] = LinkedInAgent(droidrun_config, timeout=1500)
            emit_log(f'SUCCESS: Initialized LinkedIn agent (timeout: 1500s)', 'info')
        
        # Ensure platforms list matches agents_map keys
        # Remove any platforms without initialized agents
        platforms = [p for p in platforms if p in agents_map]
        
        # Log planned posting targets
        emit_log(f'FINAL VERIFICATION:', 'step')
        emit_log(f'   Selected platforms: {platforms}', 'info')
        emit_log(f'   Agents initialized: {list(agents_map.keys())}', 'info')
        emit_log(f'   These MUST match exactly!', 'info')
        
        # Verify there are platforms to post to
        if not platforms:
            emit_log(f'ERROR: No valid platforms to post to after filtering', 'error')
            return jsonify({
                'success': False,
                'message': f'No valid platforms selected. Available: {list(agents_map.keys())}'
            }), 400
        
        # Verify platforms and agents match exactly
        if set(platforms) != set(agents_map.keys()):
            emit_log(f'ERROR: CRITICAL ERROR: Platform mismatch detected!', 'error')
            emit_log(f'   Platforms: {platforms}', 'error')
            emit_log(f'   Agents: {list(agents_map.keys())}', 'error')
            return jsonify({
                'success': False,
                'message': 'Platform selection mismatch - this should never happen'
            }), 500
        
        # Log final platform list used for posting
        emit_log(f'FINAL platform list (will post to these ONLY): {platforms}', 'step')
        emit_log(f'Total platforms to process: {len(platforms)}', 'info')
        emit_log(f'PLATFORM SELECTION LOCKED - Will NOT post to any other platforms', 'step')
        emit_log(f'Agents NOT initialized for: {[p for p in ["threads", "instagram", "twitter", "linkedin"] if p not in platforms]}', 'info')
        
        # Post to each platform with progress updates
        formatted_results = []
        total_steps = len(platforms) + 1
        
        # Set up log callback to stream agent logs to web
        set_log_callback(emit_log)
        
        # Step 1: Preparation
        emit_progress(1, total_steps, 'Preparing content', 'Setting up posting workflow...')
        emit_log('Starting content preparation...', 'info')
        if media_source_instructions:
            emit_progress(1, total_steps, 'Preparing content', f'Media Source: {media_source_instructions[:60]}...')
            emit_log(f'Media instructions: {media_source_instructions}', 'step')
        
        media_selection_strategy = None
        current_step = 2
        for platform_idx, platform in enumerate(platforms, 1):
            # Ensure platform exists in agents_map and was selected
            if platform not in agents_map:
                emit_log(f'ERROR: CRITICAL ERROR: Platform {platform} not in agents_map, ABORTING', 'error')
                emit_log(f'   This should never happen - platform was not selected!', 'error')
                continue
            
            # Verify platform was in the original selection
            if platform not in platforms:
                emit_log(f'ERROR: CRITICAL ERROR: Platform {platform} not in selected platforms, ABORTING', 'error')
                continue
            
            # Sequential processing: wait for previous platform to complete
            if platform_idx > 1:
                emit_log(f'Waiting for previous platform to complete before starting {platform.upper()}...', 'info')
                emit_log(f'Sequential mode: Processing platforms ONE BY ONE', 'step')
            
            # Log which platform we're about to post to
            emit_log(f'[{platform_idx}/{len(platforms)}] Starting posting to {platform.upper()}', 'step')
            emit_log(f'Platform {platform.upper()} confirmed as SELECTED - proceeding', 'info')
            emit_log(f'CRITICAL: Will NOT open any other platform until {platform.upper()} is COMPLETE', 'step')
            
            try:
                # Emit progress for this platform
                emit_progress(
                    current_step, 
                    total_steps, 
                    f'Posting to {platform.upper()} ({platform_idx}/{len(platforms)})',
                    f'Processing {platform.upper()} - DO NOT open other platforms until this completes'
                )
                emit_log(f'Starting {platform.upper()} agent...', 'step')
                emit_log(f'Waiting for {platform.upper()} to complete before moving to next platform...', 'info')
                
                # Run async posting in thread to avoid event loop issues
                # Pass media_source_instructions in context for agent use
                context_for_agent = {
                    "media_source_instructions": media_source_instructions
                }
                if media_selection_strategy:
                    context_for_agent["media_selection_strategy"] = media_selection_strategy
                
                # Helper function to run agent with log callback in worker thread
                def run_agent_with_logging():
                    set_log_callback(emit_log)  # Set callback in worker thread
                    return asyncio.run(
                        agents_map[platform].prepare_and_post(content_dict, context_for_agent)
                    )
                
                try:
                    import concurrent.futures
                    import time
                    # Sequential execution: wait for platform to complete
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(run_agent_with_logging)
                        # Wait for completion - this blocks until the platform finishes
                        result = future.result(timeout=1520)  # 25.33 mins for device automation with media handling
                    
                    # Confirm platform task completion
                    emit_log(f'{platform.upper()} task COMPLETED', 'success')
                    emit_log(f'Ready to proceed to next platform (if any)', 'info')
                    
                except concurrent.futures.TimeoutError:
                    result = None
                    emit_log(f'Timeout posting to {platform.upper()} after 1500s', 'error')
                    emit_log(f'{platform.upper()} did not complete - moving to next platform', 'warning')
                    raise
                except Exception as e:
                    result = None
                    emit_log(f'Exception in {platform.upper()}: {str(e)}', 'error')
                    emit_log(f'{platform.upper()} failed - moving to next platform', 'warning')
                    raise e
                
                # Update progress with result
                if result:
                    status = 'SUCCESS' if result.success else 'FAILED'
                    emit_progress(
                        current_step,
                        total_steps,
                        f'{status} {platform.upper()} - {result.reason}',
                        f'Status: {"Success" if result.success else "Failed"}'
                    )
                    emit_log(f'{status} {platform.upper()}: {result.reason}', 'success' if result.success else 'error')

                    # Capture media selection strategy after the first successful platform (with media available)
                    if result.success and not media_selection_strategy:
                        if media_source_instructions or content_dict.get("media") or content_dict.get("videos"):
                            media_selection_strategy = "photos_share_modify_reuse_same_items"
                            emit_log('Captured media selection strategy: photos_share_modify_reuse_same_items', 'info')
                    
                    formatted_results.append({
                        'platform': platform,
                        'success': result.success,
                        'reason': result.reason,
                        'error': result.error
                    })
                
                # Add delay between platforms for clean separation
                if platform_idx < len(platforms):
                    emit_log(f'Waiting 3 seconds before starting next platform...', 'info')
                    import time
                    time.sleep(3)
                    emit_log(f'Ready to start next platform', 'info')
                    
            except Exception as e:
                emit_log(f'{platform.upper()} failed: {str(e)}', 'error')
                formatted_results.append({
                    'platform': platform,
                    'success': False,
                    'reason': 'Error during posting',
                    'error': str(e)
                })
                # Even on error, add delay before next platform
                if platform_idx < len(platforms):
                    emit_log(f'Waiting 3 seconds before starting next platform...', 'info')
                    import time
                    time.sleep(3)
            finally:
                current_step += 1
        
        # Clear log callback
        set_log_callback(None)
        
        # Final completion step
        emit_progress(
            total_steps,
            total_steps,
            'All platforms completed!',
            'Your content has been posted.'
        )
        
        return jsonify({
            'success': True,
            'message': 'Content posted successfully',
            'results': formatted_results
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file uploads"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file provided'}), 400
        
        file = request.files['file']
        
        if not file or not allowed_file(file.filename):
            return jsonify({'success': False, 'message': 'Invalid file type'}), 400
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'path': filepath
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5001, help='Port to run the server on')
    args = parser.parse_args()
    
    # Run on all interfaces
    app.run(host='0.0.0.0', port=args.port, debug=True)
