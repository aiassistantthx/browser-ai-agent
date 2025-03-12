from fastapi import FastAPI, WebSocket, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from loguru import logger
import json
import asyncio
import os
from datetime import datetime

from browser_controller import browser_controller

# Configure logging
logger.add("browser_ai.log", rotation="500 MB")

app = FastAPI(title="Browser AI Agent")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active WebSocket connections
active_connections: List[WebSocket] = []

# Task storage
tasks: Dict[str, Dict[str, Any]] = {}

# Models
class Context(BaseModel):
    previous_tasks: List[str]
    browser_state: Dict[str, Any]

class TaskRequest(BaseModel):
    task_text: str
    context: Optional[Context] = None
    api_key: Optional[str] = None
    model: Optional[str] = "gpt-4"

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str

# WebSocket connection manager
async def broadcast_message(message: Dict[str, Any]):
    """Broadcast a message to all connected clients."""
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except Exception as e:
            logger.error(f"Error broadcasting message: {e}")
            active_connections.remove(connection)

# Status update callback
async def status_callback(update: Dict[str, Any]):
    """Handle status updates from the browser controller."""
    await broadcast_message(update)
    
    # Update task storage
    task_id = update.get("task_id")
    if task_id and task_id in tasks:
        tasks[task_id].update(update)

# Task handling
@app.post("/api/tasks", response_model=TaskResponse)
async def create_task(task_request: TaskRequest, background_tasks: BackgroundTasks):
    """Create and execute a new task."""
    try:
        # Generate task ID
        task_id = f"task-{datetime.now().timestamp()}"
        
        # Create task object
        task = {
            "task_id": task_id,
            "task_text": task_request.task_text,
            "context": task_request.context.dict() if task_request.context else {},
            "status": "created",
            "created_at": datetime.now().isoformat()
        }
        
        # Store task
        tasks[task_id] = task
        
        # Configure browser controller
        if task_request.api_key:
            browser_controller.api_key = task_request.api_key
        if task_request.model:
            browser_controller.model = task_request.model
            
        # Set callback for status updates
        browser_controller.callback = status_callback
        
        # Execute task in background
        background_tasks.add_task(execute_task, task)
        
        return TaskResponse(
            task_id=task_id,
            status="scheduled",
            message="Task execution scheduled"
        )
        
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def execute_task(task: Dict[str, Any]):
    """Execute a task using the browser controller."""
    try:
        result = await browser_controller.execute_task(task)
        tasks[task["task_id"]].update(result)
    except Exception as e:
        logger.error(f"Error executing task: {e}")
        tasks[task["task_id"]].update({
            "status": "failed",
            "error": str(e)
        })

@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get the current status and results of a task."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return tasks[task_id]

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                logger.error("Invalid WebSocket message format")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        active_connections.remove(websocket)
        await websocket.close()

@app.on_event("startup")
async def startup_event():
    """Initialize components on server startup."""
    try:
        await browser_controller.initialize()
        logger.info("Browser controller initialized")
    except Exception as e:
        logger.error(f"Error initializing browser controller: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on server shutdown."""
    try:
        await browser_controller.close()
        logger.info("Browser controller closed")
    except Exception as e:
        logger.error(f"Error closing browser controller: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)