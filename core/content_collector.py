"""Content collector module (deprecated - content now comes from web interface)"""

import json
import re
from typing import List, Optional, Dict

from pydantic import BaseModel, Field

from droidrun import DroidAgent, DroidrunConfig

from utils import get_logger, extract_urls
from core.models import Content


class LastMessage(BaseModel):
    """Structured output for the most recent WhatsApp message."""

    last_message_text: str = Field(description="Exact text of the most recent message")
    last_message_links: List[str] = Field(default_factory=list, description="URLs found in the most recent message")
    media: List[str] = Field(default_factory=list, description="Media descriptions/paths tied to the last message")
    videos: List[str] = Field(default_factory=list, description="Video files, links, or video descriptions from the message")
    summary: Optional[str] = Field(default=None, description="1-2 line context summary if available")


logger = get_logger(__name__)


class ContentCollector:
    """
    Legacy content collector (deprecated).
    
    Content now comes directly from the web interface.
    This class is kept for backward compatibility with examples.
    """

    def __init__(self, config: DroidrunConfig, phone_number: str = None, timeout: int = 60):
        """
        Initialize content collector (deprecated)
        
        Args:
            config: DroidrunConfig instance
            phone_number: Deprecated parameter, kept for compatibility
            timeout: Timeout for operations in seconds
        """
        self.config = config
        self.phone_number = phone_number or "deprecated"
        self.timeout = timeout

    async def collect_from_whatsapp(self) -> Optional[Content]:
        """
        Deprecated: Content collection from WhatsApp is no longer supported.
        Use the web interface to submit content directly.
        
        Returns:
            None
        """
        logger.warning("collect_from_whatsapp() is deprecated - use web interface instead")
        return None
        
        # Legacy code kept for reference only
        try:
            logger.info("This method is deprecated")
            return None

            if not result.success:
                logger.error(f"Failed to collect WhatsApp content: {result.reason}")
                return None

            # Normalize steps to handle providers that return int counts instead of a list
            steps = result.steps if isinstance(result.steps, list) else []

            # Prefer structured output when available
            last_message = result.structured_output if getattr(result, "structured_output", None) else None

            # Observation fallback: last step observation if steps exist, else reason text
            observation = steps[-1].observation if steps else (getattr(result, "reason", "") or "")

            primary_text = getattr(last_message, "last_message_text", None) or observation
            urls = getattr(last_message, "last_message_links", None) or self._extract_urls_from_result(result, observation)
            media_files = getattr(last_message, "media", None) or []
            video_files = getattr(last_message, "videos", None) or []
            
            content = Content(
                original_text=primary_text,
                extracted_urls=urls,
                media_files=media_files,
                video_files=video_files,
                context_data={
                    "source": "whatsapp",
                    "phone_number": self.phone_number,
                },
                metadata={
                    "steps_count": len(steps) if steps else (result.steps if isinstance(result.steps, int) else 0),
                    "raw_observation_included": bool(observation),
                    "used_last_message": bool(getattr(last_message, "last_message_text", None)),
                    "media_count": len(media_files),
                    "video_count": len(video_files),
                },
            )
            
            logger.info(f"Successfully collected content with {len(urls)} URLs, {len(media_files)} media, {len(video_files)} videos")
            return content
        
        except Exception as e:
            logger.error(f"Error collecting content from WhatsApp: {str(e)}", exc_info=True)
            return None

    def _create_collection_goal(self) -> str:
        """Deprecated: Create goal description for content collection agent"""
        return "Deprecated method"


    @staticmethod
    def _extract_urls_from_result(result, observation: str) -> List[str]:
        """
        Extract URLs from agent result and observation
        
        Args:
            result: Agent result object
            observation: Observation text from last step
        
        Returns:
            List of unique URLs found
        """
        urls = []
        
        # Extract from observation
        urls.extend(extract_urls(observation))
        
        # Also check all steps (defensive: handle both list and int)
        if result.steps and isinstance(result.steps, list):
            for step in result.steps:
                if hasattr(step, 'observation'):
                    urls.extend(extract_urls(step.observation))
        
        # Remove duplicates and return
        return list(set(urls))
