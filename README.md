# Browser AI Agent

A Chrome extension that enables natural language control of your browser using the powerful browser-use library.

## Features

- Natural language browser control
- Real-time task execution feedback
- Human-in-the-loop oversight
- Chat-like interface for task history
- Secure API key management
- WebSocket-based status updates

## Architecture

The project consists of two main components:

1. Chrome Extension
   - Modern React-based UI
   - Real-time status updates
   - Task history management
   - Secure communication with backend

2. Python Backend
   - FastAPI server
   - browser-use integration for reliable browser automation
   - WebSocket support for real-time updates
   - Task management and execution

## Setup

### Backend Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\\venv\\Scripts\\activate
```

2. Install dependencies:
```bash
cd backend
pip install -r requirements.txt
```

3. Install Playwright browsers:
```bash
playwright install
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your settings
```

5. Start the backend server:
```bash
python main.py
```

### Chrome Extension Setup

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" in the top right
3. Click "Load unpacked" and select the `extension` directory

## Usage

1. Click the extension icon to open the interface
2. Enter your task in natural language (e.g., "Go to Gmail and check my unread messages")
3. The AI agent will process your request and execute the necessary browser actions
4. Watch the progress in real-time and approve actions when prompted
5. View the results in the chat-like interface

## Example Tasks

- "Go to Amazon and add a MacBook Pro to my cart"
- "Find the latest AI news articles on TechCrunch and save them to a file"
- "Log into my LinkedIn account and accept all pending connection requests"
- "Open my Gmail and compose a draft email to john@example.com"

## Development

### Prerequisites

- Python 3.11+
- Node.js and npm
- Chrome browser
- OpenAI API key

### Local Development

1. Start the backend server in development mode:
```bash
cd backend
uvicorn main:app --reload --port 5000
```

2. Load the extension in Chrome as described in the setup section

3. Make changes to the code and reload the extension as needed

## Security

- API keys are stored securely and never exposed to the frontend
- All communication between extension and backend is encrypted
- Human oversight required for sensitive operations
- Rate limiting and throttling implemented
- Clear error reporting and logging

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT

## Acknowledgments

- [browser-use](https://github.com/browser-use/browser-use) - Core automation library
- [FastAPI](https://fastapi.tiangolo.com/) - Backend framework
- [Chrome Extensions](https://developer.chrome.com/docs/extensions/) - Extension development resources