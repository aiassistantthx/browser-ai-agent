// WebSocket connection
let ws = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY = 1000; // 1 second

// Active ports (connections to popup)
const ports = new Set();

// Connect to WebSocket server
function connectWebSocket() {
    if (ws) {
        ws.close();
    }

    ws = new WebSocket('ws://localhost:5000/ws');

    ws.onopen = () => {
        console.log('Connected to WebSocket server');
        reconnectAttempts = 0;
        broadcastToPopups({ type: 'connection_status', status: 'connected' });
    };

    ws.onclose = () => {
        console.log('WebSocket connection closed');
        broadcastToPopups({ type: 'connection_status', status: 'disconnected' });
        
        // Attempt to reconnect
        if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
            reconnectAttempts++;
            setTimeout(connectWebSocket, RECONNECT_DELAY * reconnectAttempts);
        }
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        broadcastToPopups({ type: 'error', message: 'WebSocket connection error' });
    };

    ws.onmessage = (event) => {
        try {
            const message = JSON.parse(event.data);
            handleWebSocketMessage(message);
        } catch (error) {
            console.error('Error parsing WebSocket message:', error);
        }
    };
}

// Handle incoming WebSocket messages
function handleWebSocketMessage(message) {
    // Broadcast message to all connected popups
    broadcastToPopups(message);

    // Handle specific message types
    switch (message.type) {
        case 'task_update':
            handleTaskUpdate(message);
            break;
        case 'browser_state':
            handleBrowserState(message);
            break;
        case 'error':
            handleError(message);
            break;
    }
}

// Handle task updates
function handleTaskUpdate(message) {
    // Update badge with task status
    if (message.status === 'running') {
        chrome.action.setBadgeText({ text: '⚡' });
        chrome.action.setBadgeBackgroundColor({ color: '#FFC107' });
    } else if (message.status === 'completed') {
        chrome.action.setBadgeText({ text: '✓' });
        chrome.action.setBadgeBackgroundColor({ color: '#4CAF50' });
        setTimeout(() => chrome.action.setBadgeText({ text: '' }), 3000);
    } else if (message.status === 'failed') {
        chrome.action.setBadgeText({ text: '!' });
        chrome.action.setBadgeBackgroundColor({ color: '#F44336' });
    }
}

// Handle browser state updates
function handleBrowserState(message) {
    // Store browser state
    chrome.storage.local.set({ browserState: message.state });
}

// Handle errors
function handleError(message) {
    console.error('Error from server:', message.error);
    chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icons/icon48.png',
        title: 'Browser AI Agent Error',
        message: message.error
    });
}

// Broadcast message to all connected popups
function broadcastToPopups(message) {
    ports.forEach(port => {
        try {
            port.postMessage(message);
        } catch (error) {
            console.error('Error sending message to popup:', error);
            ports.delete(port);
        }
    });
}

// Handle connections from popup
chrome.runtime.onConnect.addListener(port => {
    if (port.name === 'popup') {
        ports.add(port);
        
        // Send initial connection status
        port.postMessage({
            type: 'connection_status',
            status: ws && ws.readyState === WebSocket.OPEN ? 'connected' : 'disconnected'
        });

        port.onDisconnect.addListener(() => {
            ports.delete(port);
        });

        port.onMessage.addListener(async (message) => {
            if (message.type === 'execute_task') {
                await executeTask(message.task);
            }
        });
    }
});

// Execute a task
async function executeTask(task) {
    try {
        // Send task to backend
        const response = await fetch('http://localhost:5000/api/tasks', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(task)
        });

        if (!response.ok) {
            throw new Error('Failed to create task');
        }

        const taskData = await response.json();

        // Start task execution
        const executeResponse = await fetch(`http://localhost:5000/api/execute/${taskData.task_id}`, {
            method: 'POST'
        });

        if (!executeResponse.ok) {
            throw new Error('Failed to execute task');
        }

        broadcastToPopups({
            type: 'task_created',
            taskId: taskData.task_id
        });

    } catch (error) {
        console.error('Error executing task:', error);
        broadcastToPopups({
            type: 'error',
            message: 'Failed to execute task: ' + error.message
        });
    }
}

// Keep WebSocket connection alive
setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }));
    }
}, 30000);

// Initialize WebSocket connection
connectWebSocket();