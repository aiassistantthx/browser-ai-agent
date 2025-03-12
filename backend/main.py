from fastapi import FastAPI, WebSocket, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from loguru import logger
import json
import asyncio
import os

from browser_controller import browser_controller
from task_processor import task_processor

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
    context: Context

class TaskResponse(BaseModel):
    task_id: str
    parsed_intent: str
    planned_actions: List[Dict[str, Any]]
    estimated_time: str

class ExecutionResponse(BaseModel):
    status: str
    current_step: int
    total_steps: int
    current_action: str

# WebSocket connection manager
async def broadcast_message(message: Dict[str, Any]):
    """Broadcast a message to all connected clients."""
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except Exception as e:
            logger.error(f"Error broadcasting message: {e}")
            active_connections.remove(connection)

# Task handling
@app.post("/api/tasks", response_model=TaskResponse)
async def create_task(task_request: TaskRequest):
    """Create a new task from natural language input."""
    try:
        # Process the task
        task = task_processor.parse_task(task_request.task_text, task_request.context.dict())
        
        # Validate the task
        if not task_processor.validate_task(task):
            raise HTTPException(status_code=400, detail="Invalid task structure")
        
        # Store the task
        tasks[task["task_id"]] = task
        
        return TaskResponse(
            task_id=task["task_id"],
            parsed_intent=task["parsed_intent"],
            planned_actions=task["planned_actions"],
            estimated_time=task["estimated_time"]
        )
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/execute/{task_id}")
async def execute_task(task_id: str, background_tasks: BackgroundTasks):
    """Execute a task in the background."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks[task_id]
    background_tasks.add_task(_execute_task_background, task)
    
    return {
        "status": "scheduled",
        "task_id": task_id,
        "message": "Task execution started"
    }

async def _execute_task_background(task: Dict[str, Any]):
    """Execute a task and handle its lifecycle."""
    task_id = task["task_id"]
    total_steps = len(task["planned_actions"])
    
    try:
        # Update task status
        tasks[task_id]["status"] = "running"
        await broadcast_message({
            "type": "task_update",
            "task_id": task_id,
            "status": "running",
            "step": 0,
            "total_steps": total_steps
        })
        
        # Execute the task
        results = await browser_controller.execute_task(task)
        
        # Process results
        success = all(r["status"] == "success" for r in results)
        final_status = "completed" if success else "failed"
        
        # Update task status
        tasks[task_id]["status"] = final_status
        tasks[task_id]["results"] = results
        
        # Broadcast completion
        await broadcast_message({
            "type": "task_update",
            "task_id": task_id,
            "status": final_status,
            "results": results
        })
        
    except Exception as e:
        logger.error(f"Error executing task {task_id}: {e}")
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)
        
        await broadcast_message({
            "type": "task_update",
            "task_id": task_id,
            "status": "failed",
            "error": str(e)
        })

@app.get("/api/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    """Get the current status of a task."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks[task_id]
    return {
        "status": task.get("status", "unknown"),
        "results": task.get("results", []),
        "error": task.get("error"),
        "execution_time": task.get("execution_time")
    }

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