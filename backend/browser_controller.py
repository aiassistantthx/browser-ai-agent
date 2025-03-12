from browser_use import Agent
from langchain_openai import ChatOpenAI
from typing import Dict, Any, List, Optional, Callable
from loguru import logger
import asyncio
import json
import os
from datetime import datetime

class BrowserController:
    def __init__(self, api_key: str = None, model: str = "gpt-4", callback: Callable = None):
        """Initialize the browser controller with browser-use Agent.
        
        Args:
            api_key: OpenAI API key (can also be set via OPENAI_API_KEY env var)
            model: LLM model to use
            callback: Optional callback function for status updates
        """
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
            
        self.model = model
        self.callback = callback
        self._current_task: Optional[Dict[str, Any]] = None
        self._agent: Optional[Agent] = None
        
    async def initialize(self):
        """Initialize the browser-use Agent."""
        if not self._agent:
            try:
                llm = ChatOpenAI(model=self.model)
                self._agent = Agent(
                    llm=llm,
                    headless=False,  # Show browser for user visibility
                    human_in_the_loop=True  # Enable human oversight
                )
                logger.info("Browser-use Agent initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize browser-use Agent: {e}")
                raise

    async def close(self):
        """Clean up resources."""
        if self._agent:
            try:
                await self._agent.close()
                self._agent = None
                logger.info("Browser-use Agent closed")
            except Exception as e:
                logger.error(f"Error closing browser-use Agent: {e}")

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task using the browser-use Agent.
        
        Args:
            task: Dictionary containing task details
                - task_text: The natural language task description
                - context: Additional context for the task
                
        Returns:
            Dictionary containing task results
        """
        if not self._agent:
            await self.initialize()

        self._current_task = task
        task_id = task.get("task_id", f"task-{datetime.now().timestamp()}")
        
        try:
            # Update status
            await self._update_status("running", task_id)
            
            # Execute task using browser-use Agent
            result = await self._agent.run(
                task=task["task_text"],
                context=task.get("context", {}),
                max_steps=50  # Limit maximum steps for safety
            )
            
            # Process results
            success = result.get("success", False)
            status = "completed" if success else "failed"
            
            # Update task status
            await self._update_status(status, task_id, result)
            
            return {
                "task_id": task_id,
                "status": status,
                "result": result,
                "error": None if success else result.get("error")
            }
            
        except Exception as e:
            logger.error(f"Error executing task {task_id}: {e}")
            await self._update_status("failed", task_id, {"error": str(e)})
            return {
                "task_id": task_id,
                "status": "failed",
                "result": None,
                "error": str(e)
            }
        finally:
            self._current_task = None

    async def _update_status(self, status: str, task_id: str, details: Dict[str, Any] = None):
        """Send status updates through the callback if provided."""
        if self.callback:
            update = {
                "type": "task_update",
                "task_id": task_id,
                "status": status,
                "timestamp": datetime.now().isoformat()
            }
            if details:
                update.update(details)
            await self.callback(update)

    def get_current_task(self) -> Optional[Dict[str, Any]]:
        """Get information about the currently executing task."""
        return self._current_task

    @property
    def is_busy(self) -> bool:
        """Check if the agent is currently executing a task."""
        return self._current_task is not None

# Create a singleton instance
browser_controller = BrowserController()