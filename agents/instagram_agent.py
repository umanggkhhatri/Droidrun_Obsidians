"""Instagram agent for posting flashy, engaging content"""

from typing import Dict, List, Optional, Any
import json
from urllib.parse import urlparse

from droidrun import DroidrunConfig

from core.base_agent import BasePlatformAgent
from core.models import PostResult
from utils import get_logger, truncate_text


logger = get_logger(__name__)


class InstagramAgent(BasePlatformAgent):
    """
    Instagram agent for posting flashy, visually engaging content.
    
    Focus areas:
    - Flashy design and visual appeal
    - Use cases and practical benefits
    - Engaging captions with emojis
    - Hashtag optimization
    - Carousel slide ideas for multi-image posts
    """

    def __init__(self, config: DroidrunConfig, timeout: int = 60):
        """Initialize Instagram agent"""
        super().__init__(config, "instagram", timeout)
        self.caption_max_length = 2200
        self.hashtag_count = 20

    async def _prepare_content(
        self,
        content: str,
        context: Dict[str, Any],
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Prepare flashy Instagram content with captions, hashtags, and emojis
        
        Args:
            content: Original content text
            context: Crawled context data
            **kwargs: Additional arguments (unused)
        
        Returns:
            Dictionary with Instagram-specific content or None if failed
        """
        try:
            # Create comprehensive context string
            context_str = self._prepare_context_string(content, context)
            
            # Prepare prompt for content generation
            prompt = self._create_preparation_prompt(context_str)
            
            # Run agent to prepare content
            result = await self._run_droidrun_agent(prompt)

            prepared: Dict[str, Any] = {}
            if result["success"]:
                # Try to parse response
                prepared = self._extract_json_response(result["observation"]) or {}

            # Validate and fallback if needed
            if not prepared.get("caption") or len(prepared.get("caption", "")) < 40:
                logger.warning("Using fallback generator for Instagram caption")
                prepared = self._fallback_prepare_content(content, context)

            # Normalize hashtags and fields
            if not prepared.get("hashtags"):
                prepared["hashtags"] = []
            prepared["hashtags"] = [
                tag if tag.startswith("#") else f"#{tag}"
                for tag in prepared["hashtags"][: self.hashtag_count]
            ]
            prepared.setdefault("emojis", "")
            prepared.setdefault("carousel_ideas", [])

            logger.info("Instagram content prepared successfully (with fallback if needed)")
            return prepared
        
        except Exception as e:
            logger.error(f"Error preparing Instagram content: {str(e)}", exc_info=True)
            return None

    async def _post_to_platform(
        self,
        prepared_content: Dict[str, Any],
        media_urls: List[str] = None,
    ) -> PostResult:
        """
        Post content to Instagram using droidrun agent
        
        Args:
            prepared_content: Prepared content dictionary
            media_urls: Optional list of media URLs to attach
        
        Returns:
            PostResult with success status
        """
        try:
            caption = prepared_content.get("caption", "")
            hashtags = prepared_content.get("hashtags", [])
            emojis = prepared_content.get("emojis", "")
            carousel_ideas = prepared_content.get("carousel_ideas", [])
            
            # Build full caption with hashtags and emojis
            full_caption = f"{caption}\n\n{emojis}\n\n" + " ".join(hashtags)
            full_caption = truncate_text(full_caption, self.caption_max_length)
            
            # Create goal for posting
            media_str = f"Media URLs: {', '.join(media_urls)}" if media_urls else "No media"
            carousel_str = f"Carousel ideas: {json.dumps(carousel_ideas)}" if carousel_ideas else ""
            
            goal = f"""
            Post to Instagram:
            1. Open Instagram app
            2. Click on "Create" button (+ icon)
            3. Select photos/videos from: {media_str}
            4. {f"Use carousel format with these ideas: {carousel_str}" if carousel_str else ""}
            5. Add caption: {full_caption}
            6. Click "Share" to publish
            
            Return success status and any post ID or error information.
            """
            
            # Execute posting
            result = await self._run_droidrun_agent(goal)
            
            if result["success"]:
                logger.info("Instagram post successful")
                return PostResult(
                    platform="instagram",
                    success=True,
                    reason="Post published successfully",
                )
            else:
                logger.warning(f"Instagram post failed: {result['reason']}")
                return PostResult(
                    platform="instagram",
                    success=False,
                    reason=result["reason"],
                )
        
        except Exception as e:
            logger.error(f"Error posting to Instagram: {str(e)}", exc_info=True)
            return PostResult(
                platform="instagram",
                success=False,
                reason="Exception occurred during posting",
                error=str(e),
            )

    def _create_preparation_prompt(self, context: str) -> str:
        """Create prompt for content preparation"""
        return f"""
        You are an expert Instagram content creator. Adapt to the content itself: it may be personal
        (family moments, travel, kids, pets), lifestyle, creative work, or tech/product. Read the
        provided context deeply and describe what’s meaningful about it. Avoid rigid scripts—write
        naturally for humans who are scrolling fast.

        Goals:
        - Hook quickly with what matters in the content (feeling, moment, value, or story)
        - Be authentic and specific to the media/context provided (not boilerplate)
        - Keep it fun and skimmable; avoid jargon unless clearly relevant
        - If the input is a link, infer likely context and describe it accessibly

        Transform the content below into an Instagram post that fits the actual context:

        {context}

        Create a JSON response with these exact keys:
        1. "caption" (200-300 chars; hook + why it matters + soft CTA; match the actual vibe—personal or product)
        2. "hashtags" (list of up to 20 relevant hashtags—use personal/family/travel/lifestyle/creative/tech as appropriate)
        3. "emojis" (short string of 3-8 emojis that fit the vibe)
        4. "carousel_ideas" (list with 3-5 slide ideas or empty list; tailor to the content)

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
            items.append("Crawled Context:")
            for url, data in list(context.items())[:3]:  # Limit to top 3
                if isinstance(data, dict):
                    items.append(f"- {url}: {data.get('content', '')[:300]}")

        return "\n".join(items)

    def _fallback_prepare_content(self, content: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Build a flashy end-user oriented post when LLM prep fails or content is sparse."""
        # Try to derive a simple project name/slug from a URL
        project = "this project"
        emojis = "✨🚀🎯📱💡"
        default_hashtags = [
            "#tech", "#innovation", "#product", "#learning", "#buildinpublic",
            "#devlife", "#software", "#coding", "#app", "#ux", "#maker",
            "#startup", "#newrelease", "#demo", "#explore", "#discover",
            "#howitworks", "#productivity", "#design", "#wow"
        ]

        # If content looks like a URL, pull host/last path
        try:
            if isinstance(content, str) and content.startswith("http"):
                parsed = urlparse(content)
                slug = (parsed.path.strip("/") or parsed.netloc).split("/")[-1]
                if slug:
                    project = slug.replace("-", " ").replace("_", " ")
        except Exception:
            pass

        caption = (
            f"Meet {project} — a quick, fun way to try something new! "
            f"Swipe to see what it does, how it helps, and why it's awesome for your day. "
            f"Tap the link to explore more and give it a spin!"
        )

        return {
            "caption": truncate_text(caption, self.caption_max_length),
            "hashtags": default_hashtags[: self.hashtag_count],
            "emojis": emojis,
            "carousel_ideas": [
                "What it is (1-liner)",
                "Top 3 benefits",
                "How it works in 3 steps",
                "Quick demo/screenshot",
                "Try it now (CTA)"
            ],
        }
