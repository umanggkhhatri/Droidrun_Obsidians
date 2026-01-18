"""Content collector for extracting data from WhatsApp"""

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
    Collects content from WhatsApp chats.
    
    Uses droidrun agents to navigate WhatsApp and extract messages,
    links, and media information.
    """

    def __init__(self, config: DroidrunConfig, phone_number: str, timeout: int = 60):
        """
        Initialize content collector
        
        Args:
            config: DroidrunConfig instance
            phone_number: Phone number to collect content from
            timeout: Timeout for operations in seconds
        """
        self.config = config
        self.phone_number = phone_number
        self.timeout = timeout

    async def collect_from_whatsapp(self) -> Optional[Content]:
        """
        Collect content from WhatsApp chat of given number.
        
        Uses droidrun agent to:
        1. Open WhatsApp application
        2. Find the chat with specified phone number
        3. Extract messages and links from recent conversation
        4. Identify and collect any shared media
        
        Returns:
            Content object with extracted data or None if failed
        """
        try:
            logger.info(f"Starting content collection from WhatsApp: {self.phone_number}")
            
            goal = self._create_collection_goal()
            
            logger.debug(f"Running collection agent with goal: {goal[:100]}...")
            agent = DroidAgent(goal=goal, config=self.config, output_model=LastMessage)
            result = await agent.run(timeout=self.timeout)

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
        """Create goal description for content collection agent"""
        return f"""
        Collect content from WhatsApp chat:
        1. Open WhatsApp application
        2. Find and open the chat with phone number/identifier: {self.phone_number}
        3. Focus on the last incoming or outgoing message only (most recent entry)
        4. Inspect the last message for:
           - Text content (capture exact text)
           - Links/URLs (if any)
           - Media files (photos, images, videos, audio)
           - Video descriptions or captions
        5. Return ONLY the data needed to populate the structured model fields:
           - last_message_text (string - the text portion)
           - last_message_links (list of URLs in the message)
           - media (list of media file paths or descriptions - photos, images, audio, etc.)
           - videos (list of video file paths, URLs, or video descriptions if present)
           - summary (1-2 lines of context, optional)
        6. Do not include unrelated messages. Keep output concise and structured.
        """


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
