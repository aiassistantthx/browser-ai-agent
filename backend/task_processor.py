from typing import Dict, Any, List, Optional
from loguru import logger
import re
import json
import uuid
from datetime import datetime

class TaskProcessor:
    """Process natural language tasks into executable browser actions."""

    def __init__(self):
        # Common patterns for task recognition
        self.patterns = {
            "navigation": r"(?:go to|open|visit|navigate to)\s+(?:the\s+)?(?:website\s+)?([^\s]+)",
            "click": r"(?:click|press|select)\s+(?:on\s+)?(?:the\s+)?([^\.]+)",
            "type": r"(?:type|enter|input|write)\s+['\"]([^'\"]+)['\"](?:\s+(?:in|into|on)\s+(?:the\s+)?([^\.]+))?",
            "extract": r"(?:get|extract|read|find)\s+(?:the\s+)?([^\.]+)",
            "scroll": r"(?:scroll)\s+(?:to\s+)?(?:the\s+)?([^\.]+)",
            "wait": r"(?:wait|pause)\s+(?:for\s+)?(\d+)\s*(?:second|sec|s)"
        }

    def create_task_id(self) -> str:
        """Generate a unique task ID."""
        return f"task-{uuid.uuid4().hex[:8]}-{int(datetime.now().timestamp())}"

    def parse_task(self, task_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Parse natural language task into structured format."""
        task_id = self.create_task_id()
        planned_actions = []
        
        # Split complex tasks into subtasks
        subtasks = self._split_into_subtasks(task_text)
        
        for subtask in subtasks:
            actions = self._parse_subtask(subtask)
            if actions:
                planned_actions.extend(actions)

        # If no specific actions were identified, try generic navigation
        if not planned_actions:
            url = self._extract_url(task_text)
            if url:
                planned_actions.append({
                    "type": "navigate",
                    "url": self._normalize_url(url)
                })

        return {
            "task_id": task_id,
            "original_text": task_text,
            "parsed_intent": self._determine_primary_intent(task_text),
            "planned_actions": planned_actions,
            "context": context,
            "estimated_time": self._estimate_execution_time(planned_actions)
        }

    def _split_into_subtasks(self, task_text: str) -> List[str]:
        """Split complex tasks into simpler subtasks."""
        # Split on common conjunctions and sequence indicators
        splitters = r"(?:and then|then|and|after that|next|finally)"
        subtasks = re.split(splitters, task_text)
        return [st.strip() for st in subtasks if st.strip()]

    def _parse_subtask(self, subtask: str) -> List[Dict[str, Any]]:
        """Parse a single subtask into one or more actions."""
        actions = []

        # Try to match each pattern
        for intent, pattern in self.patterns.items():
            matches = re.search(pattern, subtask, re.IGNORECASE)
            if matches:
                action = self._create_action_from_match(intent, matches)
                if action:
                    actions.append(action)

        return actions

    def _create_action_from_match(self, intent: str, matches: re.Match) -> Optional[Dict[str, Any]]:
        """Create an action dictionary from a regex match."""
        if intent == "navigation":
            url = matches.group(1)
            return {
                "type": "navigate",
                "url": self._normalize_url(url)
            }
        
        elif intent == "click":
            target = matches.group(1)
            return {
                "type": "click",
                "selector": self._generate_selector(target)
            }
        
        elif intent == "type":
            text = matches.group(1)
            target = matches.group(2) if matches.groups() > 1 else None
            return {
                "type": "type",
                "text": text,
                "selector": self._generate_selector(target) if target else None
            }
        
        elif intent == "extract":
            target = matches.group(1)
            return {
                "type": "extract",
                "selector": self._generate_selector(target)
            }
        
        elif intent == "wait":
            duration = int(matches.group(1))
            return {
                "type": "wait",
                "duration": duration
            }
        
        return None

    def _normalize_url(self, url: str) -> str:
        """Normalize URLs to proper format."""
        url = url.lower().strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return url

    def _generate_selector(self, target: str) -> str:
        """Generate a CSS selector from a natural language description."""
        # This is a simplified version - in practice, you'd want more sophisticated selector generation
        selectors = []
        
        # Try to match common element types
        if re.search(r"button|link|submit", target, re.IGNORECASE):
            selectors.append(f"button, a, input[type='submit']")
        
        # Add text-based selectors
        selectors.append(f"*:contains('{target}')")
        
        # Add common form element selectors
        if re.search(r"input|text|field|box", target, re.IGNORECASE):
            selectors.append("input[type='text'], textarea")
        
        return ", ".join(selectors)

    def _determine_primary_intent(self, task_text: str) -> str:
        """Determine the primary intent of the task."""
        for intent in self.patterns:
            if re.search(self.patterns[intent], task_text, re.IGNORECASE):
                return intent
        return "unknown"

    def _estimate_execution_time(self, actions: List[Dict[str, Any]]) -> str:
        """Estimate the execution time for a series of actions."""
        # Basic time estimates per action type
        time_estimates = {
            "navigate": 3,  # seconds
            "click": 1,
            "type": 2,
            "extract": 1,
            "wait": lambda x: x.get("duration", 1)
        }
        
        total_time = sum(
            time_estimates[action["type"]]() if callable(time_estimates[action["type"]])
            else time_estimates[action["type"]]
            for action in actions
        )
        
        return f"{total_time}s"

    def validate_task(self, task: Dict[str, Any]) -> bool:
        """Validate that a task is properly structured and executable."""
        required_fields = ["task_id", "original_text", "parsed_intent", "planned_actions"]
        
        try:
            # Check required fields
            if not all(field in task for field in required_fields):
                return False
            
            # Check planned actions
            if not task["planned_actions"]:
                return False
            
            # Validate each action
            for action in task["planned_actions"]:
                if "type" not in action:
                    return False
                if action["type"] not in ["navigate", "click", "type", "extract", "wait"]:
                    return False
                
            return True
            
        except Exception as e:
            logger.error(f"Task validation error: {e}")
            return False

# Create a singleton instance
task_processor = TaskProcessor()