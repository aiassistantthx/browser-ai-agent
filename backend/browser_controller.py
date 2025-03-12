from browser_use import Browser
from typing import Dict, Any, List, Optional
from loguru import logger
import asyncio
import json

class BrowserController:
    def __init__(self):
        self._browser: Optional[Browser] = None
        self._current_task: Optional[Dict[str, Any]] = None
        self._task_queue = asyncio.Queue()

    async def initialize(self):
        """Initialize the browser instance."""
        if not self._browser:
            try:
                self._browser = await Browser.create()
                logger.info("Browser instance created successfully")
            except Exception as e:
                logger.error(f"Failed to create browser instance: {e}")
                raise

    async def close(self):
        """Close the browser instance."""
        if self._browser:
            await self._browser.close()
            self._browser = None
            logger.info("Browser instance closed")

    async def execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single browser action."""
        if not self._browser:
            await self.initialize()

        action_type = action.get("type")
        try:
            if action_type == "navigate":
                await self._browser.goto(action["url"])
                return {"status": "success", "action": "navigate", "url": action["url"]}

            elif action_type == "click":
                element = await self._browser.find_element(action["selector"])
                await element.click()
                return {"status": "success", "action": "click", "selector": action["selector"]}

            elif action_type == "type":
                element = await self._browser.find_element(action["selector"])
                await element.type(action["text"])
                return {"status": "success", "action": "type", "selector": action["selector"]}

            elif action_type == "extract":
                element = await self._browser.find_element(action["selector"])
                text = await element.text()
                return {
                    "status": "success",
                    "action": "extract",
                    "selector": action["selector"],
                    "result": text
                }

            elif action_type == "wait":
                await asyncio.sleep(action.get("duration", 1))
                return {"status": "success", "action": "wait", "duration": action.get("duration", 1)}

            else:
                raise ValueError(f"Unknown action type: {action_type}")

        except Exception as e:
            logger.error(f"Error executing action {action_type}: {e}")
            return {
                "status": "error",
                "action": action_type,
                "error": str(e)
            }

    async def execute_task(self, task: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute a complete task consisting of multiple actions."""
        self._current_task = task
        results = []

        try:
            for action in task["planned_actions"]:
                result = await self.execute_action(action)
                results.append(result)
                
                if result["status"] == "error":
                    logger.error(f"Task failed at action: {action}")
                    break

        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            results.append({
                "status": "error",
                "action": "task_execution",
                "error": str(e)
            })

        finally:
            self._current_task = None

        return results

    async def get_page_state(self) -> Dict[str, Any]:
        """Get current page state information."""
        if not self._browser:
            return {"error": "Browser not initialized"}

        try:
            return {
                "url": await self._browser.current_url(),
                "title": await self._browser.title(),
                "is_loading": await self._browser.is_loading()
            }
        except Exception as e:
            logger.error(f"Error getting page state: {e}")
            return {"error": str(e)}

    async def take_screenshot(self, path: str) -> bool:
        """Take a screenshot of the current page."""
        if not self._browser:
            return False

        try:
            await self._browser.screenshot(path)
            return True
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return False

    def get_current_task(self) -> Optional[Dict[str, Any]]:
        """Get information about the currently executing task."""
        return self._current_task

# Create a singleton instance
browser_controller = BrowserController()