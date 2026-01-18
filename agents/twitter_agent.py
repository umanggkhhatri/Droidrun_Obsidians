"""Twitter (X) agent for posting concise, scroll-stopping content"""

from typing import Dict, List, Optional, Any
import json
from urllib.parse import urlparse

from droidrun import DroidrunConfig

from core.base_agent import BasePlatformAgent
from core.models import PostResult
from utils import get_logger, truncate_text


logger = get_logger(__name__)


class TwitterAgent(BasePlatformAgent):
    """
    Twitter (X) agent for posting concise, end-user-focused content.

    Focus areas:
    - Strong hook in first line
    - Clear value/benefit in plain language
    - Minimal, relevant hashtags (2-5)
    - Optional short thread for follow-up points
    """

    def __init__(self, config: DroidrunConfig, timeout: int = 60):
        super().__init__(config, "twitter", timeout)
        self.tweet_max_length = 280
        self.hashtag_count = 5

    async def _prepare_content(
        self,
        content: str,
        context: Dict[str, Any],
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        try:
            context_str = self._prepare_context_string(content, context)
            prompt = self._create_preparation_prompt(context_str)

            result = await self._run_droidrun_agent(prompt)

            prepared: Dict[str, Any] = {}
            if result["success"]:
                prepared = self._extract_json_response(result["observation"]) or {}

            # Fallback if missing or weak
            text = prepared.get("text", "")
            if not text or len(text) < 40:
                prepared = self._fallback_prepare_content(content, context)

            # Normalize fields
            hashtags = prepared.get("hashtags", [])[: self.hashtag_count]
            hashtags = [tag if tag.startswith("#") else f"#{tag}" for tag in hashtags]
            prepared["hashtags"] = hashtags
            prepared.setdefault("thread", [])

            # Truncate tweet to fit including hashtags
            base = prepared.get("text", "")
            # Reserve ~2 chars per hashtag plus spaces
            reserve = sum(len(h) + 1 for h in hashtags)
            trimmed = truncate_text(base, max(50, self.tweet_max_length - reserve - 1))
            prepared["text"] = trimmed

            logger.info("Twitter content prepared successfully (with fallback if needed)")
            return prepared
        except Exception as e:
            logger.error(f"Error preparing Twitter content: {str(e)}", exc_info=True)
            return None

    async def _post_to_platform(
        self,
        prepared_content: Dict[str, Any],
        media_urls: List[str] = None,
    ) -> PostResult:
        try:
            text = prepared_content.get("text", "")
            hashtags = prepared_content.get("hashtags", [])
            thread = prepared_content.get("thread", [])
            video_urls = prepared_content.get("videos", [])

            full_text = text
            if hashtags:
                full_text = f"{full_text}\n\n" + " ".join(hashtags)
            
            # Combine media and video URLs
            all_media = list(set((media_urls or []) + (video_urls or [])))
            media_str = f"Media/Video URLs: {', '.join(all_media)}" if all_media else "No media/video to upload"
            thread_str = json.dumps(thread) if thread else "[]"

            goal = f"""
            Post to X (Twitter):
            1. Open the X (Twitter) app
            2. Tap the compose icon to create a new post
            3. Add the following text to the post (respect 280 char limit):\n{text}
            4. Append these hashtags:\n{' '.join(hashtags)}
            5. {f"Attach media/videos from: {media_str}" if all_media else "No media/video to upload"}
            6. If a short thread is provided, post the first tweet then reply to it with each line from this JSON list (1-3 items max):\n{thread_str}
            7. Publish the post

            Return success status and any confirmation info.
            """

            result = await self._run_droidrun_agent(goal)

            if result["success"]:
                logger.info("Twitter post successful")
                return PostResult(platform="twitter", success=True, reason="Post published successfully")
            else:
                logger.warning(f"Twitter post failed: {result['reason']}")
                return PostResult(platform="twitter", success=False, reason=result["reason"])

        except Exception as e:
            logger.error(f"Error posting to Twitter: {str(e)}", exc_info=True)
            return PostResult(
                platform="twitter",
                success=False,
                reason="Exception occurred during posting",
                error=str(e),
            )

    def _create_preparation_prompt(self, context: str) -> str:
        return f"""
        You are a world-class X (Twitter) content strategist. Adapt to the actual content: it may be personal (family, kids,
        travel, pets), lifestyle, creative work, or product/tech. Read the context deeply and write like a human, not a script.
        
        Think before you write:
        - What is the moment, feeling, or point of the content?
        - Who would care, and why? (emotion, usefulness, delight, inspiration)
        - What is the single most interesting detail to lead with?
        - Keep it authentic; avoid corporate or boilerplate tone.
        
        Write an engaging post:
        - **Hook first:** Make the opening line irresistible (curiosity, surprise, warmth, or delight)
        - **Body:** Be specific to the content; avoid generic claims. If personal, make it relatable; if product/tech, make it clear and tangible
        - **Length:** Aim 200-240 chars
        - **Hashtags:** 2-5 relevant tags that match the content (personal/lifestyle/creative/tech as appropriate)
        - **Thread:** Optional 2-4 follow-ups only if there’s more story/detail to add
        
        CONTENT TO TRANSFORM:
        {context}
        
        Respond with this JSON structure:
        {{
          "text": "Your main tweet (200-240 chars, hook first, authentic, specific to the content)",
          "hashtags": ["#Tag1", "#Tag2", "#Tag3"],
          "thread": ["Optional follow-up line 1", "Optional follow-up line 2"]
        }}
        
        Respond ONLY with valid JSON. No other text.
        """

    def _prepare_context_string(self, content: str, context: Dict[str, Any]) -> str:
        items = []
        
        # Handle both string and dict content formats
        if isinstance(content, dict):
            text = content.get("text", "")
            media = content.get("media", [])
            videos = content.get("videos", [])
            items.append(f"Original Content: {text}")
            
            if videos:
                items.append(f"Videos attached: {', '.join(videos)}")
            if media:
                items.append(f"Media attached: {', '.join(media)}")
        else:
            items.append(f"Original Content: {content}")
        
        if context:
            items.append("Context from links:")
            for url, data in list(context.items())[:2]:
                if isinstance(data, dict):
                    items.append(f"- {url}: {data.get('content', '')[:220]}")
        return "\n".join(items)

    def _fallback_prepare_content(self, content: str, context: Dict[str, Any]) -> Dict[str, Any]:
        # Derive a simple name from URL if possible
        name = "this project"
        try:
            if isinstance(content, str) and content.startswith("http"):
                parsed = urlparse(content)
                slug = (parsed.path.strip("/") or parsed.netloc).split("/")[-1]
                if slug:
                    name = slug.replace("-", " ").replace("_", " ")
        except Exception:
            pass

        text = (
            f"{name.title()} just dropped — quick, useful, and fun to try. "
            f"Give it a spin and see what you can build!"
        )
        hashtags = ["#Tech", "#BuildInPublic", "#Product", "#DevLife", "#New"]
        thread = [
            "What it does in 1 line",
            "Top 2-3 benefits",
            "Try it now — link in bio/profile",
        ]

        return {
            "text": truncate_text(text, 240),
            "hashtags": hashtags,
            "thread": thread,
        }
