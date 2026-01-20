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
                logger.info(f"Received text for posting ({len(user_text)} chars): {user_text[:150]}...")
                
                # If user provided text, use it; otherwise use a simple fallback
                if user_text and len(user_text.strip()) > 10:
                    final_text = user_text.strip()
                    # Keep full text - will be handled in _post_to_platform
                    if len(final_text) > self.caption_max_length:
                        logger.warning(f"Text ({len(final_text)} chars) exceeds limit, will truncate during posting")
                    
                    prepared = {
                        "caption": final_text,
                        "hashtags": [],
                        "emojis": "",
                        "carousel_ideas": [],
                        "media_source_instructions": media_instructions
                    }
                    logger.info(f"SUCCESS: Prepared for Instagram ({len(final_text)} chars)")
                else:
                    # Minimal fallback - let the media speak for itself
                    prepared = self._fallback_prepare_content(content, context)
                    prepared["media_source_instructions"] = media_instructions
                
                logger.info("Content prepared (simple mode) - ready for media-first posting")
                prepared["media_selection_strategy"] = context.get("media_selection_strategy", "") if isinstance(context, dict) else ""
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
            prepared.setdefault("emojis", "")
            prepared.setdefault("carousel_ideas", [])

            prepared["media_selection_strategy"] = context.get("media_selection_strategy", "") if isinstance(context, dict) else ""

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
            media_selection_strategy = prepared_content.get("media_selection_strategy", "")
            strategy_hint_text = media_selection_strategy or "Use Google Photos Share -> Modify; re-select the same items you picked previously; avoid exploring new flows."
            
            # Build full caption with emojis and hashtags
            full_caption = caption
            if emojis:
                full_caption = f"{full_caption}\n\n{emojis}"
            if hashtags:
                full_caption = f"{full_caption}\n\n" + " ".join(hashtags)
            
            full_caption = truncate_text(full_caption, self.caption_max_length)
            
            # Log the exact text being sent to the agent
            logger.info(f"POSTING CAPTION TO INSTAGRAM ({len(full_caption)} chars):")
            logger.info(f"{full_caption[:200]}...")
            
            all_media = list(set((media_urls or []) + (video_urls or [])))
            
            # Unified approach: post_chunks array (single item for Instagram)
            agent_variables = {
                "post_text": full_caption,  # Required for get_post_text() tool
                "post_chunks": [full_caption],  # Array with single chunk
                "current_chunk_index": 0,  # Always 0 for single post
                "current_chunk_number": 1,  # Always 1 for single post
                "total_chunks": 1,  # Always 1 for Instagram
            }
            
            if media_source_instructions:
                # Media path provided: enforce media-first via share sheet
                media_instruction = media_source_instructions.strip()
                
                goal = f"""
                CRITICAL: FOCUS ONLY ON INSTAGRAM - DO NOT OPEN ANY OTHER PLATFORMS
                - You are ONLY posting to Instagram right now
                - DO NOT open Twitter/X, Threads, LinkedIn, or any other social media apps
                - Complete this Instagram task FULLY before finishing
                - Return to home screen ONLY after Instagram posting is complete
                - If a prior media_selection_strategy is provided: {strategy_hint_text}
                
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

                GOOGLE PHOTOS LAYOUT (when browsing for media):
                - Top-left: Google Photos logo
                - Top-right (3 icons, right to left): Profile | Notifications | New (plus icon)
                - New button options: Create album | Collage | Highlight video | Cinematic | Animation | More
                - Bottom panel (4 buttons): Photos | Collections | Create | Search
                - CRITICAL: SCROLL TO THE TOP in Photos tab first before looking for the media
                - Photos tab shows: Media sorted by month
                - Collections tab shows: People faces | Albums | Documents | App-wise media
                - If you are NOT in Google Photos yet, you may use the device's app-opening action (e.g., open_app) to LAUNCH GOOGLE PHOTOS ONLY
                  Do NOT use it to open any other app

                Media collection (priority):
                1) Follow these EXACT instructions to locate/select media on device: {media_instruction}
                1a) CRITICAL: If opening Google Photos or any gallery app, SCROLL TO THE TOP first before doing ANY selection
                    - Always scroll back to the very top each time you re-open Photos or lose selection
                    - Do this BEFORE long-pressing or tapping any image
                    - If you already selected media successfully earlier in this session, REUSE THE SAME METHOD (Share → Modify) and pick the SAME items; do not re-explore new flows
                1b) PREFERRED MULTI-PHOTO METHOD (use before other methods):
                    - Select the FIRST required photo
                    - Tap the "Share" button
                    - In the share sheet, tap "Modify" to add more photos
                    - In the modify view, select the remaining required photos (e.g., specific date/position)
                    - Confirm selection, then proceed back to the share sheet to pick Instagram
                    - This is the primary strategy; use scrolling only if Modify flow is unavailable
                1c) SCROLL-BASED METHOD (fallback):
                    - Select ONE media first, then SCROLL from the MIDDLE OF THE SCREEN to find the NEXT media item
                    * Scroll the media grid UPWARDS (swipe from bottom area towards top)
                    * Start scroll gesture a little UPWARDS from the bottom of visible screen to avoid overlay issues
                    - Tap to add it to selection; repeat for each additional media
                    - Always scroll from the middle/center of the screen, NOT from edges
                    - Do it one by one; this is the fallback if Modify is not available
                1d) MEDIA SELECTION STRATEGY NOTES:
                    - Image ordering in Photos and in-app "Add media" is NOT trustworthy - they may show different orders
                    - CRITICAL: You CANNOT select media separately and share them one by one to posting apps - must select all together
                    - CRITICAL: NEVER use Instagram's in-app media picker/gallery - it shows media from all sources in wrong order
                    - ALWAYS use Google Photos via share sheet - this ensures correct media selection
                    - If needed: try collection/album view; try different tabs; try adjacent-image select/deselect/reselect
                2) IMPORTANT: After selecting media, if you cannot find the share button or it's hidden behind a banner/overlay:
                   - Try swiping up slightly to reveal hidden UI elements
                   - Try tapping on empty space to dismiss any overlays or popups
                   - Look for share icons in corners or bottom of screen
                   - If needed, long-press on the media to get context menu with share option
                   - Scroll/swipe the thumbnail bar if the selected image seems hidden
                3) Use the system share sheet to share the selected media to Instagram.
                   SELECTION RULE (priority order):
                   1. PRIMARY: Try to find and tap "Instagram Feed" option
                      - Scroll the share sheet DOWN to search for it
                      - Scroll all the way to the BOTTOM if needed
                      - After tapping, WAIT 2 SECONDS for Instagram to load the page
                   2. FALLBACK #1: If "Instagram Feed" not found, tap "Instagram Reels" option
                      - Scroll to find this option
                      - After tapping, WAIT 2 SECONDS for Instagram to load the page
                   3. FALLBACK #2: If neither Feed nor Reels found, tap plain "Instagram" option
                      - This is the last resort option
                      - After tapping, WAIT 2 SECONDS for Instagram to load the page
                   4. NEVER tap tiles with "Stories" or "Messages" subtitles
                   - This opens the Instagram composer with media attached

                SHARE-SHEET FALLBACK:
                - If tapping Instagram lands you on the Instagram home feed instead of the composer:
                   * Press BACK twice quickly (within ~1s) to exit to the share sheet
                   * If you see a toast like "Tap again to exit", press BACK once more immediately
                   * If still in Instagram after two back presses:
                       - Press HOME to return to the Android home screen
                       - Use open_app to launch Google Photos (com.google.android.apps.photos)
                       - Re-select the same media and open the share sheet again
                       - Tap "Instagram Feed" option in the share sheet

                Compose in Instagram:
                4) Confirm media thumbnails are visible in the composer BEFORE typing any text. If not, go back and re-share the media.
                5) Call get_post_text() to retrieve the caption ({len(full_caption)} characters)
                6) Store the returned text in a variable: caption_content = get_post_text()
                   - The function will print "POST_TEXT: <actual text>"
                   - This printed text is what you MUST type
                7) Type the ENTIRE returned caption into the caption field using: type(text=caption_content, index=...)
                   - DO NOT type your own example text or placeholders
                   - DO NOT type test strings like "This is a test post..."
                   - ONLY use the variable caption_content that contains the ACTUAL text
                8) After typing the caption, you MUST find and tap the "Share" button to publish (DO NOT leave as draft)

                CRITICAL NOTES:
                - get_post_text() returns the complete Instagram caption
                - Instagram posts are single-post only (no chunking/threading)
                - You MUST use the exact text from get_post_text() - do NOT generate your own
                - NEVER type hardcoded strings - ALWAYS use caption_content
                - You MUST publish the post - drafts are NOT acceptable; tap Share to post

                9) CRITICAL: Finding the Share button - check these locations in order:
                   a) Look at the BOTTOM of the screen first - there may be a "Share" button in the bottom toolbar
                   b) Look at the TOP-RIGHT corner - there may be a "Share" or "Post" button
                   c) Scroll down slightly if the button is hidden - sometimes the Share button is below the visible area
                   d) Look for any button that says "Share", "Post", "Publish", or has a share icon (arrow pointing right/up)
                   e) The Share button might be in a fixed position at the bottom, even if you need to scroll to see it
                10) Once you find the Share button, tap it immediately
                11) CRITICAL: If you cannot find the Share button:
                    - Try scrolling the screen up or down to reveal hidden buttons
                    - Look for any button with text like "Share", "Post", "Next", or "Done"
                    - Check if there's a button at the very bottom edge of the screen
                    - The Share button is ESSENTIAL - you MUST find and tap it to publish
                12) After tapping Share, wait for confirmation that the post was published
                13) The screen should change (e.g., return to feed, show "Your post has been shared", or show the post in your profile). If you see a Draft prompt, choose Share/Publish, NOT Save Draft.
                14) Verify the post is done by checking if the screen changed or if you see a success confirmation

                CRITICAL: The get_post_text() tool returns the ACTUAL caption from the system.
                You MUST use that exact text - do NOT generate or summarize your own caption.
                CRITICAL: After writing the description, you MUST find and tap the Share button - this is REQUIRED to publish.
                CRITICAL: The Share button might be at the bottom OR top-right - check both locations.
                CRITICAL: If the Share button is not visible, scroll to reveal it - it's essential for publishing.
                CRITICAL: Wait for the screen to change or show confirmation before considering the post done.

                After posting:
                15) After tapping Share and seeing confirmation, IMMEDIATELY press BACK button once
                    - This ensures you exit the post view and can see your feed/profile
                    - CRITICAL: Wait 1 second after the post is published, then press BACK
                    - This helps ensure the post is fully processed
                16) After pressing BACK, press HOME button (or swipe up from bottom) to return to Android home screen
                17) Verify you're on the home screen before finishing

                Return success status and any confirmation info.
                """
            else:
                # No explicit media instructions: still enforce media-first via Google Photos share sheet
                goal = f"""
                CRITICAL: FOCUS ONLY ON INSTAGRAM - DO NOT OPEN ANY OTHER PLATFORMS
                - You are ONLY posting to Instagram right now
                - DO NOT open Twitter/X, Threads, LinkedIn, or any other social media apps
                - Complete this Instagram task FULLY before finishing
                - Return to home screen ONLY after Instagram posting is complete

                ALWAYS ATTACH MEDIA VIA GOOGLE PHOTOS SHARE SHEET:
                - Do NOT rely on Instagram's in-app media picker; it may show wrong order/sources
                - Use Google Photos to select media and share to Instagram so thumbnails attach in the composer

                GOOGLE PHOTOS LAYOUT:
                - Top-left: Google Photos logo
                - Bottom panel: Photos | Collections | Create | Search
                - CRITICAL: SCROLL TO THE TOP in Photos tab first to find recent media
                - If you are NOT in Google Photos yet, use open_app to launch com.google.android.apps.photos

                Steps:
                1) Press HOME to ensure you're on the Android home screen (if inside any app)
                2) Use open_app to launch Google Photos (com.google.android.apps.photos)
                3) SCROLL TO THE TOP in Photos tab
                4) Select the target media using the one-by-one selection method:
                   - Select ONE media first, verify selection indicator
                   - Scroll from the middle of the screen, tap next media to add to selection
                   - Repeat until all required items are selected
                5) Open the system share sheet
                6) SELECT THE CORRECT INSTAGRAM OPTION:
                   SELECTION RULE (priority order):
                   1. PRIMARY: Try to find and tap "Instagram Feed" option
                      - Scroll the share sheet DOWN to search for it
                      - Scroll all the way to the BOTTOM if needed
                      - After tapping, WAIT 2 SECONDS for Instagram to load the page
                   2. FALLBACK #1: If "Instagram Feed" not found, tap "Instagram Reels" option
                      - Scroll to find this option
                      - After tapping, WAIT 2 SECONDS for Instagram to load the page
                   3. FALLBACK #2: If neither Feed nor Reels found, tap plain "Instagram" option
                      - This is the last resort option
                      - After tapping, WAIT 2 SECONDS for Instagram to load the page
                   4. NEVER tap tiles with "Stories" or "Messages" subtitles
                   - This opens the Instagram composer with media attached

                SHARE-SHEET FALLBACK:
                - If tapping Instagram lands you on the Instagram home feed (not composer):
                   * Press BACK twice quickly (within ~1s) to exit to the share sheet
                   * If a toast says "Tap again to exit", press BACK once more immediately
                   * If still inside Instagram after two back presses: press HOME, reopen Google Photos via open_app,
                       re-select media, open share sheet again, and tap "Instagram Feed" option

                Compose in Instagram:
                7) Confirm media thumbnails are visible in the composer BEFORE typing any text
                   - If thumbnails are missing, go BACK and re-share via Google Photos
                8) Call get_post_text() to retrieve the caption ({len(full_caption)} characters)
                9) Store the returned text: caption_content = get_post_text()
                   - The function prints "POST_TEXT: <actual text>"; type exactly that
                10) Type the ENTIRE caption into the caption field using only caption_content
                11) Find and tap the "Share" button to publish

                CRITICAL NOTES:
                - You MUST use the exact text from get_post_text()
                - NEVER type hardcoded strings; ONLY use caption_content
                - You MUST publish (tap Share); do not leave as draft
                - If Share button not visible, scroll; check bottom and top-right

                After posting:
                12) After tapping Share and seeing confirmation, IMMEDIATELY press BACK button once
                    - This ensures you exit the post view and can see your feed/profile
                    - CRITICAL: Wait 1 second after the post is published, then press BACK
                    - This helps ensure the post is fully processed
                13) After pressing BACK, press HOME to return to Android home screen
                14) Return success status with confirmation info
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
        emojis = ""

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
            f"Just discovered something amazing! {project}\n\n"
            f"Swipe to see more and let me know what you think in the comments!"
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

