"""Base agent class for all platform-specific agents"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
import asyncio
import sys
import io
import contextlib
from contextlib import redirect_stdout, redirect_stderr

from droidrun import DroidAgent, DroidrunConfig

from utils import get_logger, extract_json_from_text
from core.models import Content, PlatformPost, PostResult

logger = get_logger(__name__)

# Global log callback - can be set by web app to stream logs
_log_callback: Optional[Callable[[str, str], None]] = None

def set_log_callback(callback: Callable[[str, str], None]):
    """Set a callback for agent logs. Callback receives (message, log_type)"""
    global _log_callback
    _log_callback = callback

def emit_agent_log(message: str, log_type: str = 'info'):
    """Emit a log message via the callback if set"""
    global _log_callback
    if _log_callback:
        _log_callback(message, log_type)


class BasePlatformAgent(ABC):
    """Abstract base class for platform-specific agents"""

    def __init__(self, config: DroidrunConfig, platform_name: str, timeout: int = 60):
        """
        Initialize base agent
        
        Args:
            config: DroidrunConfig instance
            platform_name: Name of the platform (instagram, linkedin, etc.)
            timeout: Timeout for agent operations in seconds
        """
        self.config = config
        self.platform_name = platform_name
        self.timeout = timeout
        self.logger = get_logger(f"{__name__}.{platform_name}")

    async def prepare_and_post(
        self,
        content: str,
        context: Dict[str, Any],
        media_urls: List[str] = None,
        **kwargs
    ) -> PostResult:
        """
        Main method to prepare content and post it
        
        Args:
            content: Original content text
            context: Context data from crawled URLs
            media_urls: Optional media URLs to include
            **kwargs: Additional platform-specific arguments
        
        Returns:
            PostResult with success status and details
        """
        try:
            self.logger.info(f"Preparing {self.platform_name} post...")
            
            # Prepare platform-specific content
            prepared_content = await self._prepare_content(content, context, **kwargs)
            if not prepared_content:
                return PostResult(
                    platform=self.platform_name,
                    success=False,
                    reason="Failed to prepare content",
                )
            
            # Post to platform
            self.logger.info(f"Posting to {self.platform_name}...")
            post_result = await self._post_to_platform(prepared_content, media_urls)
            
            return post_result

        except Exception as e:
            self.logger.error(f"Error in prepare_and_post: {str(e)}", exc_info=True)
            return PostResult(
                platform=self.platform_name,
                success=False,
                reason="Exception occurred",
                error=str(e),
            )

    @abstractmethod
    async def _prepare_content(
        self,
        content: str,
        context: Dict[str, Any],
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Prepare content specific to platform
        
        Should be implemented by subclasses to create platform-specific content
        
        Args:
            content: Original content
            context: Context data
            **kwargs: Additional arguments
        
        Returns:
            Dictionary with prepared content or None if failed
        """
        pass

    @abstractmethod
    async def _post_to_platform(
        self,
        prepared_content: Dict[str, Any],
        media_urls: List[str] = None,
    ) -> PostResult:
        """
        Post prepared content to platform using droidrun agent
        
        Should be implemented by subclasses
        
        Args:
            prepared_content: Dictionary with prepared content
            media_urls: Optional media URLs
        
        Returns:
            PostResult with success status
        """
        pass

    async def _run_droidrun_agent(self, goal: str, timeout: int = None, variables: dict = None, custom_tools: dict = None) -> Dict[str, Any]:
        """
        Run a droidrun agent with given goal
        
        Args:
            goal: Goal description for the agent
            timeout: Custom timeout (uses self.timeout if not provided)
            variables: Optional variables dict to pass to agent (accessible via custom tools)
            custom_tools: Optional custom tools dict for the agent
        
        Returns:
            Dictionary with result details
        """
        try:
            timeout = timeout or self.timeout
            self.logger.debug(f"Running droidrun agent with goal: {goal[:100]}...")
            emit_agent_log(f"🚀 Starting agent with goal: {goal[:80]}...", 'step')

            # Build custom tools for accessing variable
            tools_to_use = custom_tools or {}
            
            # Add a get_post_text tool if post_text is in variables
            if variables and "post_text" in variables:
                post_text_length = len(str(variables["post_text"]))
                
                def get_post_text(*, shared_state=None, **kwargs) -> str:
                    """Get the post text from variables that must be typed into Threads."""
                    if shared_state:
                        text = shared_state.custom_variables.get("post_text", "")
                        emit_agent_log(f"📋 get_post_text() called, returning {len(text)} chars", 'info')
                        return text
                    return ""
                
                tools_to_use["get_post_text"] = {
                    "arguments": [],
                    "description": f"REQUIRED: Call this tool to get the exact post text ({post_text_length} characters) that MUST be typed into Threads. The returned string is the complete post - use it exactly as returned.",
                    "function": get_post_text
                }
                emit_agent_log(f"📝 Registered get_post_text tool with {post_text_length} chars", 'info')

            # Instantiate agent per run with explicit goal, variables, and custom tools
            agent = DroidAgent(
                goal=goal, 
                config=self.config, 
                variables=variables or {},
                custom_tools=tools_to_use if tools_to_use else None
            )
            emit_agent_log(f"📱 Agent initialized, running (timeout: {timeout}s)...", 'info')

            # Start agent and stream events in real-time
            handler = agent.run()

            async def _stream_events():
                """Stream only thoughts (💭) and actions (🖱️) to the terminal UI."""
                try:
                    async for event in handler.stream_events():
                        try:
                            name = event.__class__.__name__

                            # Only emit thoughts and actions - skip everything else
                            
                            # Executor actions with thoughts
                            if name == "ExecutorActionEvent":
                                thought = getattr(event, 'thought', '')
                                desc = getattr(event, 'description', '')
                                if thought:
                                    emit_agent_log(f"💭 {thought}", 'info')
                                if desc:
                                    emit_agent_log(f"🖱️ {desc}", 'action')

                            # CodeAct response events (contain thoughts)
                            elif name == "CodeActResponseEvent":
                                thought = getattr(event, 'thought', None)
                                if thought:
                                    emit_agent_log(f"💭 {thought}", 'info')

                            # Action events (clicks, text input, etc)
                            elif "ActionEvent" in name and name != "ExecutorActionEvent":
                                action = getattr(event, 'action', None)
                                if action:
                                    emit_agent_log(f"🖱️ {str(action)[:150]}", 'action')
                            
                            # App launch actions
                            elif "AppEvent" in name or "StartApp" in name:
                                app_name = getattr(event, 'app', None) or getattr(event, 'package', None)
                                if app_name:
                                    emit_agent_log(f"🖱️ Opening {app_name}", 'action')

                            # All other events are silently ignored for cleaner terminal output
                            
                        except Exception as inner:
                            # Never let logging break streaming
                            self.logger.debug(f"Stream event handling error: {inner}")
                except Exception as stream_err:
                    self.logger.debug(f"Event stream closed: {stream_err}")

            # Consume stream concurrently while waiting for result
            stream_task = asyncio.create_task(_stream_events())
            
            # Await final result with timeout
            result = await asyncio.wait_for(handler, timeout=timeout)
            
            # Ensure stream task is complete
            with contextlib.suppress(Exception):
                await asyncio.wait_for(stream_task, timeout=2.0)

            steps = result.steps if isinstance(result.steps, list) else []
            observation = steps[-1].observation if steps else (getattr(result, "reason", "") or "")
            steps_count = len(steps) if steps else (result.steps if isinstance(result.steps, int) else 0)
            
            # Log step details from result object
            if steps:
                emit_agent_log(f"📋 Processing {len(steps)} steps...", 'step')
                for i, step in enumerate(steps, 1):
                    action = getattr(step, 'action', None) or getattr(step, 'code', 'unknown')
                    obs = getattr(step, 'observation', '')[:150] if hasattr(step, 'observation') else ''
                    emit_agent_log(f"  Step {i}/{len(steps)}: {action[:60]}", 'action')
                    if obs:
                        emit_agent_log(f"    → {obs[:100]}", 'info')
            
            if result.success:
                emit_agent_log(f"✅ Agent completed successfully ({steps_count} steps)", 'success')
            else:
                emit_agent_log(f"❌ Agent failed: {result.reason}", 'error')

            return {
                "success": result.success,
                "reason": result.reason,
                "observation": observation,
                "steps_count": steps_count,
            }
        
        except asyncio.TimeoutError:
            self.logger.warning(f"Agent execution timed out after {timeout}s")
            emit_agent_log(f"⏱️ Agent timed out after {timeout}s", 'error')
            return {
                "success": False,
                "reason": f"Execution timed out after {timeout}s",
                "observation": "",
                "steps_count": 0,
            }
        
        except Exception as e:
            self.logger.error(f"Error running droidrun agent: {str(e)}", exc_info=True)
            emit_agent_log(f"💥 Agent error: {str(e)}", 'error')
            return {
                "success": False,
                "reason": f"Exception: {str(e)}",
                "observation": "",
                "steps_count": 0,
            }

    def _extract_json_response(self, text: str) -> Dict[str, Any]:
        """Extract JSON from agent response text"""
        return extract_json_from_text(text)

    async def _retry_operation(self, operation, max_retries: int = 3, delay: int = 2):
        """
        Retry an async operation with exponential backoff
        
        Args:
            operation: Async callable to retry
            max_retries: Maximum retry attempts
            delay: Initial delay between retries in seconds
        
        Returns:
            Result of operation if successful
        
        Raises:
            Exception: If all retries fail
        """
        for attempt in range(max_retries):
            try:
                return await operation()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                wait_time = delay * (2 ** attempt)  # Exponential backoff
                self.logger.warning(f"Attempt {attempt + 1} failed. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
