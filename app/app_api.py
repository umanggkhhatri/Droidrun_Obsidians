"""Flask backend for content posting via Droidrun agents"""

import os
import asyncio
import json
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import base64
from typing import List, Dict, Any

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config.settings import get_config
from core.orchestrator import ContentOrchestrator
from droidrun import DroidrunConfig

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = '/tmp/content_uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4', 'mov', 'avi'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load Droidrun config
try:
    cfg_path = os.path.join(os.path.expanduser("~"), ".droidrun", "config.yaml")
    droidrun_config = DroidrunConfig.from_yaml(cfg_path)
except Exception as e:
    print(f"Warning: Could not load Droidrun config: {e}")
    droidrun_config = None


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def create_content_object(text: str, links: str, media_files: List[str]) -> Dict[str, Any]:
    """Create a content dict for the orchestrator"""
    link_list = [l.strip() for l in links.split(',') if l.strip()]
    
    return {
        "text": text,
        "media": media_files,
        "videos": [m for m in media_files if m.endswith(('.mp4', '.mov', '.avi'))],
        "urls": link_list,
    }


@app.route('/api/post', methods=['POST'])
def post_content():
    """Main endpoint to receive content and post to platforms"""
    try:
        if not droidrun_config:
            return jsonify({'error': 'Droidrun config not loaded'}), 500
        
        # Get form data
        text = request.form.get('text', '').strip()
        links = request.form.get('links', '').strip()
        platforms_str = request.form.get('platforms', '[]')
        platforms = json.loads(platforms_str)
        
        if not text and not request.files:
            return jsonify({'error': 'No text or media provided'}), 400
        
        if not platforms:
            return jsonify({'error': 'No platforms selected'}), 400
        
        # Save uploaded media
        media_files = []
        if 'media' in request.files:
            files = request.files.getlist('media')
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    media_files.append(filepath)
        
        # Update environment for platforms
        for platform in ['threads', 'twitter', 'instagram', 'linkedin']:
            os.environ[f'{platform.upper()}_ENABLED'] = 'true' if platform in platforms else 'false'
        
        # Create content object
        content_dict = create_content_object(text, links, media_files)
        
        # Get app config
        app_config = get_config('development')
        
        # Run async orchestration
        results = asyncio.run(
            orchestrate_posting(droidrun_config, app_config, content_dict, platforms)
        )
        
        return jsonify({
            'success': True,
            'message': 'Content posted',
            'results': results,
        })
    
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


async def orchestrate_posting(
    droidrun_config: DroidrunConfig,
    app_config: Any,
    content_dict: Dict[str, Any],
    platforms: List[str],
) -> Dict[str, Any]:
    """Orchestrate posting to selected platforms"""
    
    orchestrator = ContentOrchestrator(
        droidrun_config,
        phone_number='app_upload',  # Special marker for non-WhatsApp source
        app_config=app_config,
    )
    
    # Override content collection—use provided content directly
    from core.models import Content
    orchestrator.collected_content = Content(
        original_text=content_dict['text'],
        extracted_urls=content_dict['urls'],
        media_files=content_dict['media'],
        video_files=content_dict['videos'],
        context_data={'source': 'app_upload'},
    )
    
    # Skip crawling (no URLs to crawl from app)
    orchestrator.context_data = {}
    
    # Post to selected platforms only
    results = {}
    platform_sequence = [
        ('twitter', orchestrator.twitter_agent),
        ('threads', orchestrator.threads_agent),
        ('instagram', orchestrator.instagram_agent),
        ('linkedin', orchestrator.linkedin_agent),
    ]
    
    for platform_name, agent in platform_sequence:
        if platform_name not in platforms:
            results[platform_name] = {'skipped': True}
            continue
        
        if not app_config.PLATFORMS[platform_name]["enabled"]:
            results[platform_name] = {'skipped': True, 'reason': 'disabled'}
            continue
        
        try:
            result = await agent.prepare_and_post(
                content_dict,
                media_urls=content_dict['media'],
            )
            results[platform_name] = {
                'success': result.success,
                'reason': result.reason,
                'error': result.error,
            }
        except Exception as e:
            results[platform_name] = {
                'success': False,
                'error': str(e),
            }
    
    return results


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'droidrun_ready': droidrun_config is not None})


if __name__ == '__main__':
    print("Starting Content Poster API...")
    print("API: http://localhost:5000")
    print("Make sure ~/.droidrun/config.yaml is set up and GOOGLE_API_KEY is exported")
    app.run(debug=True, port=5000, host='0.0.0.0')
