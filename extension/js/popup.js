// State management
let state = {
  status: 'idle',
  messages: [],
};

// DOM Elements
const chatContainer = document.getElementById('chatContainer');
const userInput = document.getElementById('userInput');
const submitBtn = document.getElementById('submitBtn');
const statusText = document.getElementById('statusText');
const statusIndicator = document.getElementById('statusIndicator');

// Event Listeners
submitBtn.addEventListener('click', handleSubmit);
userInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSubmit();
  }
});

// Main submit handler
async function handleSubmit() {
  const text = userInput.value.trim();
  if (!text) return;

  // Add user message to chat
  addMessage('user', text);
  userInput.value = '';

  // Update status
  updateStatus('thinking');

  try {
    // Send to backend
    const response = await sendTask(text);
    
    // Add agent response to chat
    addMessage('agent', response.result);
    
    // Update status
    updateStatus('idle');
  } catch (error) {
    console.error('Error:', error);
    addMessage('agent', 'Sorry, there was an error processing your request.');
    updateStatus('error');
  }
}

// Helper functions
function addMessage(type, content) {
  const message = {
    type,
    content,
    timestamp: new Date().toISOString()
  };

  state.messages.push(message);
  renderMessage(message);
  saveMessages();
}

function renderMessage(message) {
  const messageElement = document.createElement('div');
  messageElement.classList.add('message');
  messageElement.classList.add(`${message.type}-message`);
  messageElement.textContent = message.content;
  
  chatContainer.appendChild(messageElement);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function updateStatus(status) {
  state.status = status;
  statusText.textContent = status.charAt(0).toUpperCase() + status.slice(1);
  statusIndicator.className = 'status-indicator';
  if (status !== 'idle') {
    statusIndicator.classList.add(status);
  }
}

async function sendTask(text) {
  // TODO: Replace with actual backend endpoint
  const response = await fetch('http://localhost:5000/api/tasks', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      task_text: text,
      context: {
        previous_tasks: state.messages
          .filter(m => m.type === 'user')
          .map(m => m.content),
        browser_state: {}
      }
    })
  });

  if (!response.ok) {
    throw new Error('Network response was not ok');
  }

  return response.json();
}

function saveMessages() {
  chrome.storage.local.set({ messages: state.messages });
}

// Load saved messages on startup
chrome.storage.local.get(['messages'], (result) => {
  if (result.messages) {
    state.messages = result.messages;
    state.messages.forEach(renderMessage);
  }
});