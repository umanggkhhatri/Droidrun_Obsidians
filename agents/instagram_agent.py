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
    - Hashtag optimization (up to 30)
    - Carousel slide ideas for multi-image posts
    """

    def __init__(self, config: DroidrunConfig, timeout: int = 1500):
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
            content: Original content text or dict with text/media
            context: Crawled context data
            **kwargs: Additional arguments (unused)
        
        Returns:
            Dictionary with Instagram-specific content or None if failed
        """
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
                    final_text = user_text.strip()
                    if len(final_text) > self.caption_max_length - 200:  # Reserve space for hashtags
                        final_text = truncate_text(final_text, self.caption_max_length - 200)
                    
                    prepared = {
                        "caption": final_text,
                        "hashtags": self._generate_default_hashtags(),
                        "emojis": "✨🚀📸",
                        "carousel_ideas": [],
                        "media_source_instructions": media_instructions
                    }
                    logger.info(f"✅ Prepared caption for posting ({len(final_text)} chars)")
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
            prepared.setdefault("emojis", "✨🚀📸")
            prepared.setdefault("carousel_ideas", [])

            logger.info("Instagram content prepared successfully")
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
            video_urls = prepared_content.get("videos", [])
            media_source_instructions = prepared_content.get("media_source_instructions", "")
            
            # Build full caption with emojis and hashtags
            full_caption = caption
            if emojis:
                full_caption = f"{full_caption}\n\n{emojis}"
            if hashtags:
                full_caption = f"{full_caption}\n\n" + " ".join(hashtags)
            
            full_caption = truncate_text(full_caption, self.caption_max_length)
            
            # Log the exact text being sent to the agent
            logger.info(f"🎯 POSTING CAPTION TO INSTAGRAM ({len(full_caption)} chars):")
            logger.info(f"📝 {full_caption[:200]}...")
            
            all_media = list(set((media_urls or []) + (video_urls or [])))
            
            # Pass caption as variable (not embedded in goal string)
            agent_variables = {
                "post_text": full_caption,
            }
            
            if media_source_instructions:
                # Media path provided: enforce media-first via share sheet
                media_instruction = media_source_instructions.strip()
                
                goal = f"""
                Create an Instagram post using media collected FIRST, then add text.

                INSTAGRAM COMPOSER LAYOUT:
                - CREATE button: TOP-LEFT corner of screen (plus icon)
                - After media selection: Caption input (top)
                - Attachment options (below caption): Location tag | Tag people | Accessibility | Advanced settings
                - Share button: Top-right corner (says "Share")
                - Bottom nav: Home | Reels | Messages (center) | Search | Profile

                INSTAGRAM APP LAYOUT:
                - Top bar: CREATE/+ (top-left) | Logo (center) | Notifications (top-right)
                - Bottom nav: Home | Reels | Messages (center) | Search | Profile
                - Create button: TOP-LEFT corner of screen (plus icon)
                - Share sheet: Look for "instagram ▾" dropdown - choose Feed/Reels/Stories as appropriate

                GOOGLE PHOTOS LAYOUT (when browsing for media):
                - Top-left: Google Photos logo
                - Top-right (3 icons, right to left): Profile | Notifications | New (plus icon)
                - New button options: Create album | Collage | Highlight video | Cinematic | Animation | More
                - Bottom panel (4 buttons): Photos | Collections | Create | Search
                - CRITICAL: SCROLL TO THE TOP in Photos tab first before looking for the media
                - Photos tab shows: Media sorted by month
                - Collections tab shows: People faces | Albums | Documents | App-wise media

                Media collection (priority):
                1) Follow these EXACT instructions to locate/select media on device: {media_instruction}
                1a) CRITICAL: If opening Google Photos or any gallery app, SCROLL TO THE TOP first before looking for the media
                1b) ⭐ IMPORTANT USEFUL METHOD - TRY THIS FIRST: In Google Photos, select ONE media first, then SCROLL to find more media and tap them to add to selection
                   * STEP-BY-STEP PROCESS:
                     1. Select the FIRST media item
                     2. Verify it's selected (check for selection indicator)
                     3. SCROLL from the MIDDLE OF THE SCREEN to find the NEXT media item
                        - Scroll the media grid UPWARDS (swipe from bottom area towards top)
                        - Start scroll gesture a little UPWARDS from the bottom of visible screen to avoid overlay issues
                     4. Tap to add it to selection
                     5. Repeat steps 3-4 for each additional media
                   * CRITICAL: Always scroll from the middle/center of the screen, NOT from edges
                   * This is the MOST RELIABLE way to select multiple images
                   * Don't try to select all at once - do it ONE BY ONE in sequence
                   * ALWAYS attempt this method BEFORE trying any fallback approaches
                1c) MEDIA SELECTION STRATEGY:
                   - Image ordering in Photos and in-app "Add media" is NOT trustworthy - they may show different orders
                   - CRITICAL: You CANNOT select media separately and share them one by one to posting apps - must select all together
                   - CRITICAL: NEVER use Instagram's in-app media picker/gallery - it shows media from all sources in wrong order
                   - ALWAYS use Google Photos via share sheet - this ensures correct media selection
                                     - If the scroll method above fails, try these alternative approaches:
                     * Select one image, then swipe up or down, then tap another image to add it to selection
                     * Try using the collection/album view if direct media browsing fails
                     * Try selecting from different tabs (Photos tab vs Collections tab)
                     * If a specific image won't select, try selecting adjacent images first, then deselect and reselect
                2) IMPORTANT: After selecting media, if you cannot find the share button or it's hidden behind a banner/overlay:
                   - Try swiping up slightly to reveal hidden UI elements
                   - Try tapping on empty space to dismiss any overlays or popups
                   - Look for share icons in corners or bottom of screen
                   - If needed, long-press on the media to get context menu with share option
                   - Scroll/swipe the thumbnail bar if the selected image seems hidden
                3) Use the system share sheet to share the selected media to Instagram.
                   IMPORTANT: There are MULTIPLE Instagram sharing options available in the share sheet:
                   - DO NOT use "Instagram Messages" or "Instagram Direct" - these are for DMs only
                   - ALWAYS look for and use "instagram ▾" (with down arrow symbol) option
                   - This is the correct option that opens the Instagram composer with media attached
                   - Do NOT use plain "Instagram", "Instagram Feed", "Instagram Reels", or "Instagram Stories" unless "instagram ▾" is not available
                   - The goal is to open the Instagram composer with the media already attached, NOT to send a message

                Compose in Instagram:
                4) Call get_post_text() to retrieve the caption ({len(full_caption)} characters)
                5) Store the returned text in a variable: caption_content = get_post_text()
                6) Type the ENTIRE returned caption into the caption field using: type(text=caption_content, index=...)
                7) After typing the caption, look for the "Share" button
                8) IMPORTANT: The Share button is located at the BOTTOM of the screen (not top-right)
                9) Tap the Share button at the BOTTOM
                10) Wait for confirmation that the post was published - the screen should change (e.g., return to feed or show success message)
                11) Verify the post is done by checking if the screen changed or if you see a success confirmation
                12) Return success status only after confirming the post was published.

                CRITICAL: The get_post_text() tool returns the ACTUAL caption from the system.
                You MUST use that exact text - do NOT generate or summarize your own caption.
                CRITICAL: After writing the description, you MUST tap the Share button at the BOTTOM of the screen.
                CRITICAL: Wait for the screen to change or show confirmation before considering the post done.
                
                After posting:
                13) After confirming the post was published, press HOME button (or swipe up from bottom) to return to Android home screen
                14) Verify you're on the home screen before finishing
                
                Return success status and any confirmation info.
                """
            else:
                # No media path: open Instagram directly
                media_str = f"Media URLs: {', '.join(all_media)}" if all_media else "No external media"
                
                goal = f"""
                Post to Instagram:
                
                INSTAGRAM COMPOSER LAYOUT:
                - CREATE button: TOP-LEFT corner of screen (plus/+ icon)
                - After selecting media: Caption input field (top)
                - Attachment options (below caption): Location tag | Tag people | Accessibility
                - Share button: Top-right corner
                - Bottom navigation: Home | Reels | Messages | Search | Profile
                
                1. Open Instagram app (com.instagram.android)
                2. Tap the CREATE "+" button (TOP-LEFT corner) to start a new post
                3. Select photos/videos from gallery or: {media_str}
                4. Proceed to caption screen
                5. Call get_post_text() to retrieve the caption ({len(full_caption)} characters)
                6. Store the returned text: caption_content = get_post_text()
                7. Type the ENTIRE caption into the caption field
                8. After typing the caption, look for the "Share" button
                9) IMPORTANT: The Share button is located at the BOTTOM of the screen (not top-right)
                10) Tap the Share button at the BOTTOM
                11) Wait for confirmation that the post was published - the screen should change (e.g., return to feed or show success message)
                12) Verify the post is done by checking if the screen changed or if you see a success confirmation
                13) Return success status only after confirming the post was published

                CRITICAL: The get_post_text() tool returns the ACTUAL caption from the system.
                You MUST use that exact text - do NOT generate your own caption.
                CRITICAL: After writing the description, you MUST tap the Share button at the BOTTOM of the screen.
                CRITICAL: Wait for the screen to change or show confirmation before considering the post done.
                
                Return success status and any confirmation info.
                """
            
            result = await self._run_droidrun_agent(goal, variables=agent_variables)
            
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

    def _generate_default_hashtags(self) -> List[str]:
        """Generate default hashtags for Instagram"""
        return [
            "#instagood", "#photooftheday", "#beautiful", "#happy",
            "#picoftheday", "#instadaily", "#amazing", "#style",
            "#life", "#bestoftheday", "#instacool", "#explore"
        ]

    def _fallback_prepare_content(self, content: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Build a flashy end-user oriented post when LLM prep fails or content is sparse."""
        project = "this"
        emojis = "✨🚀🎯📱💡"

        try:
            if isinstance(content, str) and content.startswith("http"):
                parsed = urlparse(content)
                slug = (parsed.path.strip("/") or parsed.netloc).split("/")[-1]
                if slug:
                    project = slug.replace("-", " ").replace("_", " ")
            elif isinstance(content, dict):
                text = content.get("text", "")
                if text:
                    project = text[:50]
        except Exception:
            pass

        caption = (
            f"Just discovered something amazing! {project} ✨\n\n"
            f"Swipe to see more and let me know what you think in the comments! 👇"
        )

        return {
            "caption": truncate_text(caption, self.caption_max_length - 200),
            "hashtags": self._generate_default_hashtags(),
            "emojis": emojis,
            "carousel_ideas": [
                "What it is",
                "Key highlights",
                "Why it matters",
                "Try it yourself"
            ],
        }

