"""LinkedIn agent for posting formal, technical content"""

from typing import Dict, List, Optional, Any
import json

from droidrun import DroidrunConfig

from core.base_agent import BasePlatformAgent
from core.models import PostResult
from utils import get_logger, truncate_text


logger = get_logger(__name__)


class LinkedInAgent(BasePlatformAgent):
    """
    LinkedIn agent for posting formal, technically detailed content.
    
    Focus areas:
    - Technical approach and architecture
    - Problem-solving perspective
    - Industry applications and insights
    - Thought leadership tone
    - Professional hashtags
    """

    def __init__(self, config: DroidrunConfig, timeout: int = 60):
        """Initialize LinkedIn agent"""
        super().__init__(config, "linkedin", timeout)
        self.post_max_length = 3000
        self.hashtag_count = 15

    async def _prepare_content(
        self,
        content: str,
        context: Dict[str, Any],
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Prepare formal, technical LinkedIn content
        
        Args:
            content: Original content text
            context: Crawled context data
            **kwargs: Additional arguments (unused)
        
        Returns:
            Dictionary with LinkedIn-specific content or None if failed
        """
        try:
            # Create comprehensive context string
            context_str = self._prepare_context_string(content, context)
            
            # Prepare prompt for content generation
            prompt = self._create_preparation_prompt(context_str)
            
            # Run agent to prepare content
            result = await self._run_droidrun_agent(prompt)
            
            if not result["success"]:
                logger.error(f"Failed to prepare LinkedIn content: {result['reason']}")
                return None
            
            # Parse response
            prepared = self._extract_json_response(result["observation"])
            
            # Validate required fields
            if not prepared.get("headline"):
                logger.warning("No headline in response, using fallback")
                prepared["headline"] = "Exciting Project Update"
            
            if not prepared.get("description"):
                logger.warning("No description in response, using original content")
                prepared["description"] = truncate_text(content, self.post_max_length)
            
            if not prepared.get("hashtags"):
                prepared["hashtags"] = []
            
            # Ensure hashtags are properly formatted
            prepared["hashtags"] = [
                tag if tag.startswith("#") else f"#{tag}"
                for tag in prepared["hashtags"][:self.hashtag_count]
            ]
            
            logger.info("LinkedIn content prepared successfully")
            return prepared
        
        except Exception as e:
            logger.error(f"Error preparing LinkedIn content: {str(e)}", exc_info=True)
            return None

    async def _post_to_platform(
        self,
        prepared_content: Dict[str, Any],
        media_urls: List[str] = None,
    ) -> PostResult:
        """
        Post content to LinkedIn using droidrun agent
        
        Args:
            prepared_content: Prepared content dictionary
            media_urls: Optional list of media URLs to attach
        
        Returns:
            PostResult with success status
        """
        try:
            headline = prepared_content.get("headline", "")
            description = prepared_content.get("description", "")
            hashtags = prepared_content.get("hashtags", [])
            cta = prepared_content.get("cta", "")
            
            # Build full post content
            full_post = f"{headline}\n\n{description}\n\n" + " ".join(hashtags)
            if cta:
                full_post += f"\n\n{cta}"
            
            full_post = truncate_text(full_post, self.post_max_length)
            
            # Create goal for posting
            media_str = f"Media URLs: {', '.join(media_urls)}" if media_urls else "No media"
            
            goal = f"""
            Post to LinkedIn:
            1. Open LinkedIn app
            2. Click on "Start a post" button
            3. Add the following content:
            {full_post}
            4. {f"Upload media from: {media_str}" if media_urls else "No media to upload"}
            5. Click "Post" to publish
            
            Return success status and any confirmation information.
            """
            
            # Execute posting
            result = await self._run_droidrun_agent(goal)
            
            if result["success"]:
                logger.info("LinkedIn post successful")
                return PostResult(
                    platform="linkedin",
                    success=True,
                    reason="Post published successfully",
                )
            else:
                logger.warning(f"LinkedIn post failed: {result['reason']}")
                return PostResult(
                    platform="linkedin",
                    success=False,
                    reason=result["reason"],
                )
        
        except Exception as e:
            logger.error(f"Error posting to LinkedIn: {str(e)}", exc_info=True)
            return PostResult(
                platform="linkedin",
                success=False,
                reason="Exception occurred during posting",
                error=str(e),
            )

    def _create_preparation_prompt(self, context: str) -> str:
        """Create prompt for content preparation"""
        return f"""
        You are a technical thought leader on LinkedIn specializing in software architecture and innovation.
        
        Transform the following content into a professional, technically detailed LinkedIn post 
        that demonstrates expertise and provides industry value:
        
        {context}
        
        Create a JSON response with these exact keys:
        1. "headline" (60-80 chars, professional and engaging)
        2. "description" (300-500 chars, covering technical approach, problem solved, and applications)
        3. "hashtags" (list of 15 professional and technical hashtags)
        4. "cta" (call-to-action for engagement, optional)
        
        Respond ONLY with valid JSON, no other text.
        """

    def _prepare_context_string(self, content: str, context: Dict[str, Any]) -> str:
        """Prepare context string for the prompt (handles dict content with media/videos)"""
        items: List[str] = []

        if isinstance(content, dict):
            text = content.get("text", "")
            media = content.get("media", [])
            videos = content.get("videos", [])
            items.append(f"Original Content: {text}")
            if videos:
                items.append(f"Videos: {', '.join(videos)}")
            if media:
                items.append(f"Media: {', '.join(media)}")
        else:
            items.append(f"Original Content: {content}")

        if context:
            items.append("Crawled Technical Context:")
            for url, data in list(context.items())[:3]:  # Limit to top 3
                if isinstance(data, dict):
                    content_preview = data.get('content', '')[:500]
                    items.append(f"- Source: {url}\n  Details: {content_preview}")

        return "\n".join(items)
