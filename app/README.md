# Social Media Automation App

Mobile app for posting to Instagram, LinkedIn, X, and Threads.

## Quick Start

### Prerequisites
- Node.js v16+
- Python 3.8+
- Expo CLI

### Setup

```bash
# Install dependencies
npm install

# Start Flask backend
source venv/bin/activate
python app.py

# In another terminal, start Expo
npm start
```

### Running the App
- Scan QR code with Expo Go (phone)
- Or press `a` for Android emulator

## Project Structure
```
├── App.js              # React Native entry
├── app.py              # Flask backend
├── src/
│   ├── screens/        # 6 mobile screens
│   ├── services/       # API layer
│   ├── context/        # State management
│   └── components/     # Reusable UI components
├── package.json        # Node dependencies
├── app.json            # Expo config
└── requirements.txt    # Python dependencies
```

## API Configuration
Update your machine IP in `src/services/ApiService.js`:
```javascript
const API_BASE_URL = 'http://YOUR_IP:5001';
```

## Features
✓ Photo upload
✓ Description writing
✓ Platform selection
✓ Content preview
✓ Ready for Droidrun integration
