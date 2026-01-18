"""
Social Media Automation Web Application
Allows users to upload photos, write descriptions, and post to multiple platforms
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from pathlib import Path
import os
import uuid
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_DESCRIPTION_LENGTH = 5000

# Create upload folder if it doesn't exist
Path(UPLOAD_FOLDER).mkdir(exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Global state for tracking uploads
upload_sessions = {}


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_session_id():
    """Generate unique session ID."""
    return str(uuid.uuid4())


@app.route('/')
def index():
    """Serve the main application page."""
    return render_template('index.html')


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file upload."""
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        
        # Check if file is selected
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        # Check file type
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'Invalid file type. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({
                'success': False,
                'error': f'File too large. Maximum size: 50MB'
            }), 400
        
        # Save file
        session_id = generate_session_id()
        filename = f"{session_id}_{secure_filename(file.filename)}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        file.save(filepath)
        
        # Store session info
        upload_sessions[session_id] = {
            'filename': filename,
            'original_filename': file.filename,
            'filepath': filepath,
            'uploaded_at': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'filename': filename,
            'message': 'File uploaded successfully'
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/preview/<session_id>')
def preview_file(session_id):
    """Get preview of uploaded file."""
    try:
        if session_id not in upload_sessions:
            return jsonify({'success': False, 'error': 'Invalid session'}), 404
        
        filename = upload_sessions[session_id]['filename']
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/validate-description', methods=['POST'])
def validate_description():
    """Validate description input."""
    try:
        data = request.get_json()
        description = data.get('description', '').strip()
        
        if not description:
            return jsonify({
                'success': False,
                'error': 'Description cannot be empty'
            }), 400
        
        if len(description) > MAX_DESCRIPTION_LENGTH:
            return jsonify({
                'success': False,
                'error': f'Description too long. Maximum: {MAX_DESCRIPTION_LENGTH} characters'
            }), 400
        
        return jsonify({
            'success': True,
            'length': len(description),
            'message': 'Description is valid'
        }), 200
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/preview-content', methods=['POST'])
def preview_content():
    """Preview how content will look on each platform."""
    try:
        data = request.get_json()
        description = data.get('description', '').strip()
        
        if not description:
            return jsonify({
                'success': False,
                'error': 'Description is required'
            }), 400
        
        # Generate platform-specific previews
        adapted_content = {
            'instagram': description[:2200],
            'linkedin': description[:3000],
            'x': description[:280],
            'threads': description[:500]
        }
        
        # Add character counts
        platform_previews = {}
        platforms_config = {
            'instagram': {'max': 2200, 'icon': '📷'},
            'linkedin': {'max': 3000, 'icon': '💼'},
            'threads': {'max': 500, 'icon': '🧵'},
            'x': {'max': 280, 'icon': '𝕏'}
        }
        
        for platform, content in adapted_content.items():
            config = platforms_config.get(platform, {})
            platform_previews[platform] = {
                'content': content,
                'length': len(content),
                'max_length': config.get('max', 5000),
                'icon': config.get('icon', ''),
                'fits': len(content) <= config.get('max', 5000)
            }
        
        return jsonify({
            'success': True,
            'previews': platform_previews
        }), 200
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/post', methods=['POST'])
def post_content():
    """Post content to selected platforms (ready for Droidrun integration)."""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        description = data.get('description', '').strip()
        platforms = data.get('platforms', [])
        
        # Validate inputs
        if not session_id or session_id not in upload_sessions:
            return jsonify({'success': False, 'error': 'Invalid session'}), 400
        
        if not description:
            return jsonify({'success': False, 'error': 'Description is required'}), 400
        
        if not platforms or not isinstance(platforms, list):
            return jsonify({'success': False, 'error': 'At least one platform must be selected'}), 400
        
        # Get file path
        filepath = upload_sessions[session_id]['filepath']
        
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'error': 'Upload file not found'}), 400
        
        # Validate platforms
        valid_platforms = ['instagram', 'linkedin', 'threads', 'x']
        platforms = [p.lower() for p in platforms if p.lower() in valid_platforms]
        
        if not platforms:
            return jsonify({'success': False, 'error': 'Invalid platform selection'}), 400
        
        # Prepare content for each platform
        results = {}
        for platform in platforms:
            results[platform] = {
                'success': True,
                'message': f'Ready to post to {platform}',
                'content': prepare_content_for_platform(description, platform),
                'image_path': filepath
            }
        
        # TODO: Connect Droidrun integration here
        # Import and use Droidrun agents to actually post
        
        return jsonify({
            'success': True,
            'results': results,
            'message': f'Content prepared for {len(platforms)} platforms. Ready for Droidrun integration.'
        }), 200
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# Placeholder for platform posting - user will implement Droidrun integration
def prepare_content_for_platform(description, platform):
    """Prepare content for specific platform (placeholder for Droidrun integration)."""
    return {
        'description': description,
        'platform': platform,
        'timestamp': datetime.now().isoformat()
    }


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    }), 200


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors."""
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
