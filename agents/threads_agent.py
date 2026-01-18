"""Threads agent for posting conversational, authentic content"""

from typing import Dict, List, Optional, Any
import json
from urllib.parse import urlparse

from droidrun import DroidrunConfig

from core.base_agent import BasePlatformAgent
from core.models import PostResult
from utils import get_logger, truncate_text


logger = get_logger(__name__)


class ThreadsAgent(BasePlatformAgent):
    """
    Threads agent for posting authentic, conversational content.

    Focus areas:
    - Natural, casual tone
    - Personal insights and stories
    - Minimal hashtags (0-3)
    - Thread format for longer thoughts
    """

    def __init__(self, config: DroidrunConfig, timeout: int = 60):
        super().__init__(config, "threads", timeout)
        self.post_max_length = 700  # Increased for longer, better posts
        self.hashtag_count = 3

    async def _prepare_content(
        self,
        content: str,
        context: Dict[str, Any],
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        try:
            # Check for media_source_instructions FIRST
            media_instructions = context.get("media_source_instructions", "")
            if not media_instructions and isinstance(content, dict):
                media_instructions = content.get("media_source_instructions", "")
            
            # If media instructions exist, use simple text preparation (NO device agent)
            # This prevents the agent from opening any apps before media collection
            if media_instructions:
                logger.info(f"Media instructions detected - using simple text prep (no device interaction)")
                logger.info(f"Media instructions: {media_instructions[:80]}...")
                
                # Extract user's text directly - don't run device agent
                if isinstance(content, dict):
                    user_text = content.get("text", "")
                else:
                    user_text = str(content) if content else ""
                
                # Log the text we received
                logger.info(f"📝 Received text for posting ({len(user_text)} chars): {user_text[:150]}...")
                
                # If user provided text, use it; otherwise use a simple fallback
                if user_text and len(user_text.strip()) > 10:
                    # Don't truncate aggressively - keep the full transformed text
                    final_text = user_text.strip()
                    if len(final_text) > self.post_max_length:
                        final_text = truncate_text(final_text, self.post_max_length - 10)
                    
                    prepared = {
                        "text": final_text,
                        "hashtags": [],
                        "thread": [],
                        "media_source_instructions": media_instructions
                    }
                    logger.info(f"✅ Prepared text for posting ({len(final_text)} chars)")
                else:
                    # Minimal fallback - let the media speak for itself
                    prepared = self._fallback_prepare_content(content, context)
                    prepared["media_source_instructions"] = media_instructions
                
                logger.info("Content prepared (simple mode) - ready for media-first posting")
                return prepared
            
            # No media instructions - use full agent-based content generation
            context_str = self._prepare_context_string(content, context)
            prompt = self._create_preparation_prompt(context_str)

            result = await self._run_droidrun_agent(prompt)

            prepared: Dict[str, Any] = {}
            if result["success"]:
                prepared = self._extract_json_response(result["observation"]) or {}

            # Fallback if missing or weak
            text = prepared.get("text", "")
            if not text or len(text) < 50:
                prepared = self._fallback_prepare_content(content, context)

            # Normalize fields
            hashtags = prepared.get("hashtags", [])[: self.hashtag_count]
            hashtags = [tag if tag.startswith("#") else f"#{tag}" for tag in hashtags]
            prepared["hashtags"] = hashtags
            prepared.setdefault("thread", [])

            # Truncate main post
            base = prepared.get("text", "")
            trimmed = truncate_text(base, self.post_max_length - 10)
            prepared["text"] = trimmed

            logger.info("Threads content prepared successfully")
            return prepared
        except Exception as e:
            logger.error(f"Error preparing Threads content: {str(e)}", exc_info=True)
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
            media_source_instructions = prepared_content.get("media_source_instructions", "")

            full_text = text
            if hashtags:
                full_text = f"{full_text}\n\n" + " ".join(hashtags)
            
            # Log the exact text being sent to the agent
            logger.info(f"🎯 POSTING TEXT TO THREADS ({len(full_text)} chars):")
            logger.info(f"📝 {full_text}")
            
            all_media = list(set((media_urls or []) + (video_urls or [])))
            
            # Build goal: if media instructions provided, collect & share to Threads first
            thread_str = json.dumps(thread) if thread else "[]"

            # Pass text and thread as variables (not embedded in goal string)
            # This ensures the agent uses the exact transformed text without reading/reinterpreting
            agent_variables = {
                "post_text": full_text,
                "thread_items": thread,
                "thread_items_json": thread_str
            }
            
            if media_source_instructions:
                # Media path provided: enforce media-first via share sheet
                media_instruction = media_source_instructions.strip()
                
                goal = f"""
                Create a Threads post using media collected FIRST, then add text.

                Media collection (priority):
                1) Follow these EXACT instructions to locate/select media on device: {media_instruction}
                2) Use the system share sheet to share the selected media to Threads (com.instagram.barcelona)
                   so the Threads composer opens with the media already attached.

                Compose in Threads:
                3) Call get_post_text() to retrieve the post content ({len(full_text)} characters)
                4) Store the returned text in a variable: post_content = get_post_text()
                5) Type the ENTIRE returned text into the composer using: type(text=post_content, index=...)
                6) Publish the post.

                CRITICAL: The get_post_text() tool returns the ACTUAL post content from the system.
                You MUST use that exact text - do NOT generate or summarize your own text.
                
                Return success status and any confirmation info.
                """
            else:
                # No media path: ignore media, just post text/thread
                goal = f"""
                Post to Threads:
                1. Open the Threads app
                2. Tap the compose icon to create a new post
                3. Call get_post_text() to retrieve the post content ({len(full_text)} characters)
                4. Store the returned text in a variable: post_content = get_post_text()
                5. Type the ENTIRE returned text into the composer using: type(text=post_content, index=...)
                6. Publish the post.

                CRITICAL: The get_post_text() tool returns the ACTUAL post content from the system.
                You MUST use that exact text - do NOT generate or summarize your own text.
                
                Return success status and any confirmation info.
                """

            result = await self._run_droidrun_agent(goal, variables=agent_variables)

            if result["success"]:
                logger.info("Threads post successful")
                return PostResult(platform="threads", success=True, reason="Post published successfully")
            else:
                logger.warning(f"Threads post failed: {result['reason']}")
                return PostResult(platform="threads", success=False, reason=result["reason"])

        except Exception as e:
            logger.error(f"Error posting to Threads: {str(e)}", exc_info=True)
            return PostResult(
                platform="threads",
                success=False,
                reason="Exception occurred during posting",
                error=str(e),
            )

    def _create_preparation_prompt(self, context: str) -> str:
        return f"""
        You are crafting a post for Threads (by Instagram) - a platform for authentic, conversational content.
        
        Threads is about:
        - Real talk, personal insights, behind-the-scenes thoughts
        - Casual, approachable tone (like texting a friend)
        - Longer form than Twitter but still concise
        - Minimal to no hashtags (0-3 max, only if truly relevant)
        - Threading for deeper thoughts
        
        Create a Threads post:
        - **Opening:** Start with a relatable hook or personal observation
        - **Body:** Share genuine insights, learnings, or experiences (400-500 chars)
        - **Tone:** Conversational, authentic, human - avoid corporate speak
        - **Hashtags:** 0-3 only if they add value
        - **Thread:** Break longer thoughts into 2-4 follow-up posts for readability
        
        Transform this content into a Threads post:

        {context}

        Respond with JSON:
        {{
          "text": "Main post (400-500 chars, authentic and conversational)",
          "hashtags": ["#Optional", "#Max3"],
          "thread": ["Follow-up thought 1", "Follow-up thought 2"]
        }}

        Respond ONLY with valid JSON.
        """

    def _prepare_context_string(self, content: str, context: Dict[str, Any]) -> str:
        items = []
        
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
                    items.append(f"- {url}: {data.get('content', '')[:300]}")
        return "\n".join(items)

    def _fallback_prepare_content(self, content: str, context: Dict[str, Any]) -> Dict[str, Any]:
        name = "this"
        try:
            if isinstance(content, str) and content.startswith("http"):
                parsed = urlparse(content)
                slug = (parsed.path.strip("/") or parsed.netloc).split("/")[-1]
                if slug:
                    name = slug.replace("-", " ").replace("_", " ")
        except Exception:
            pass

        text = (
            f"Just found {name} and had to share. "
            f"It's one of those things that makes you think differently about how we build and create. "
            f"Worth checking out if you're into this kind of stuff."
        )
        hashtags = []
        thread = [
            "What caught my attention was how thoughtfully it's designed.",
            "Sometimes the simple things make the biggest difference.",
        ]

        return {
            "text": truncate_text(text, self.post_max_length - 10),
            "hashtags": hashtags,
            "thread": thread,
        }
