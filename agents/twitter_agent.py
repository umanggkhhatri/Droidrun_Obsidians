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

    def __init__(self, config: DroidrunConfig, timeout: int = 1500):
        super().__init__(config, "twitter", timeout)
        self.tweet_max_length = 280  # Twitter/X API limit
        self.chunk_cutoff = 224  # Start looking for sentence breaks at 20% before limit (280 * 0.8 = 224)
        self.hashtag_count = 5

    def _split_into_chunks(self, text: str, max_chunks: int = 25) -> List[str]:
        """
        Split text into chunks with max 280 characters (Twitter limit), breaking at sentence boundaries.
        
        Strategy:
        - Start looking for sentence breaks at 224 chars (20% before 280 limit)
        - Each chunk must end with sentence-ending punctuation or break cleanly
        - No text overlap between chunks
        - Each chunk is independent and complete
        """
        if not text or len(text) <= self.tweet_max_length:
            return [text]
        
        chunks = []
        remaining = text.strip()
        
        while remaining and len(chunks) < max_chunks:
            # If remaining text fits in one chunk, add it and done
            if len(remaining) <= self.tweet_max_length:
                chunks.append(remaining)
                break
            
            # Look for sentence break starting from 20% before max (224 chars for 280 limit)
            search_range = remaining[:self.chunk_cutoff + 56]  # Search window: 224-280 chars
            sentence_found = False
            
            # Try to find sentence endings, working backwards from the end
            for end_marker in ['. ', '? ', '! ', '.\n', '?\n', '!\n']:
                pos = search_range.rfind(end_marker)
                if pos > 100:  # Need at least 100 chars for meaningful tweet
                    end_pos = pos + 1  # Include the punctuation
                    chunk = remaining[:end_pos].strip()
                    if len(chunk) > 0:
                        chunks.append(chunk)
                        remaining = remaining[end_pos:].lstrip()
                        sentence_found = True
                        break
            
            if sentence_found:
                continue
            
            # Try line break
            line_pos = search_range.rfind('\n')
            if line_pos > 100:
                chunk = remaining[:line_pos].strip()
                chunks.append(chunk)
                remaining = remaining[line_pos:].strip()
                continue
            
            # Try word boundary
            space_pos = search_range.rfind(' ')
            if space_pos > 100:
                chunk = remaining[:space_pos].strip()
                chunks.append(chunk)
                remaining = remaining[space_pos:].strip()
            else:
                # Force break at max length
                chunk = remaining[:self.tweet_max_length].strip()
                chunks.append(chunk)
                remaining = remaining[self.tweet_max_length:].strip()
        
        # Add any remaining text as final chunk
        if remaining and len(chunks) < max_chunks:
            chunks.append(remaining)
        
        return chunks if chunks else [text]

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
            if media_instructions:
                logger.info(f"Media instructions detected - using simple text prep (no device interaction)")
                logger.info(f"Media instructions: {media_instructions[:80]}...")
                
                # Extract user's text directly
                if isinstance(content, dict):
                    user_text = content.get("text", "")
                else:
                    user_text = str(content) if content else ""
                
                logger.info(f"Received text for posting ({len(user_text)} chars): {user_text[:150]}...")
                
                if user_text and len(user_text.strip()) > 10:
                    # Keep full text for chunking in _post_to_platform
                    final_text = user_text.strip()
                    if len(final_text) > self.tweet_max_length:
                        logger.info(f"Text ({len(final_text)} chars) will be chunked into multiple tweets")
                    
                    prepared = {
                        "text": final_text,
                        "hashtags": [],
                        "thread": [],
                        "media_source_instructions": media_instructions
                    }
                    logger.info(f"SUCCESS: Prepared for Twitter ({len(final_text)} chars)")
                else:
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

            # Fallback if missing or weak
            text = prepared.get("text", "")
            if not text or len(text) < 10:
                prepared = self._fallback_prepare_content(content, context)

            # Normalize fields
            hashtags = prepared.get("hashtags", [])[: self.hashtag_count]
            hashtags = [tag if tag.startswith("#") else f"#{tag}" for tag in hashtags]
            prepared["hashtags"] = hashtags
            prepared.setdefault("thread", [])

            # Get the prepared text
            base = prepared.get("text", "")
            
            # Enforce Twitter max length (280 chars)
            # Don't truncate aggressively - keep full text for chunking in _post_to_platform
            if len(base) > self.tweet_max_length:
                logger.warning(f"WARNING: Prepared text ({len(base)} chars) exceeds Twitter limit ({self.tweet_max_length} chars)")
                logger.info(f"Text will be chunked into multiple tweets during posting phase")
                # Keep full text for chunking in _post_to_platform
                prepared["text"] = base
            else:
                prepared["text"] = base

            prepared["media_selection_strategy"] = context.get("media_selection_strategy", "") if isinstance(context, dict) else ""
            logger.info("Twitter content prepared successfully")
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
            media_source_instructions = prepared_content.get("media_source_instructions", "")
            media_selection_strategy = prepared_content.get("media_selection_strategy", "")
            strategy_hint_text = media_selection_strategy or "Use Google Photos Share -> Modify; re-select the same items you picked previously; avoid exploring new flows."

            full_text = text
            if hashtags:
                full_text = f"{full_text}\n\n" + " ".join(hashtags)
            
            # Log the exact text being sent to the agent
            logger.info(f"POSTING TWEET TO X ({len(full_text)} chars):")
            logger.info(f"{full_text}")
            
            # Split text into chunks with 280 char max, breaking at sentences
            chunks = self._split_into_chunks(full_text)
            logger.info(f"Split into {len(chunks)} tweets for thread")
            for i, chunk in enumerate(chunks, 1):
                logger.info(f"  Tweet {i} ({len(chunk)} chars): {chunk[:50]}...")
            
            all_media = list(set((media_urls or []) + (video_urls or [])))
            thread_str = json.dumps(thread) if thread else "[]"
            
            # Post each chunk as part of a thread
            posted_chunks = 0
            
            for chunk_idx, chunk_text in enumerate(chunks):
                chunk_num = chunk_idx + 1
                total_chunks = len(chunks)
                
                # Unified approach: post_chunks array + current index
                agent_variables = {
                    "post_text": chunk_text,  # Required for get_post_text() tool
                    "post_chunks": chunks,  # Array of all chunks
                    "current_chunk_index": chunk_idx,  # 0-indexed
                    "current_chunk_number": chunk_num,  # 1-indexed
                    "total_chunks": total_chunks,
                    "thread_items": thread,
                    "thread_items_json": thread_str
                }
                
                if chunk_idx == 0 and media_source_instructions:
                    # First tweet with media: enforce media-first via share sheet
                    media_instruction = media_source_instructions.strip()
                    
                    goal = f"""
                    CRITICAL: FOCUS ONLY ON X (TWITTER) - DO NOT OPEN ANY OTHER PLATFORMS
                    - You are ONLY posting to X (Twitter) right now
                    - DO NOT open Threads, Instagram, LinkedIn, or any other social media apps
                    - Complete this X (Twitter) task FULLY before finishing
                    - Return to home screen ONLY after X (Twitter) posting is complete
                    
                    Create an X (Twitter) post using media collected FIRST, then add text (Tweet {chunk_num}/{total_chunks}).

                    X (TWITTER) COMPOSER LAYOUT:
                    - Compose button: BLUE PLUS icon (bottom-right, above bottom navigation)
                    - Composer text input: Top of screen
                    - Attachment icons (horizontal row below text): Media | GIF | Poll | Emoji | Schedule
                    - Post/Tweet button: Top-right corner (says "Post")
                    - Bottom nav: Home | Search | Grok AI (center) | Notifications | Inbox

                    GOOGLE PHOTOS LAYOUT (when browsing for media):
                    - Top-left: Google Photos logo
                    - Top-right (3 icons, right to left): Profile | Notifications | New (plus icon)
                    - New button options: Create album | Collage | Highlight video | Cinematic | Animation | More
                    - Bottom panel (4 buttons): Photos | Collections | Create | Search
                    - CRITICAL: SCROLL TO THE TOP in Photos tab first before looking for the media
                    - Photos tab shows: Media sorted by month
                    - Collections tab shows: People faces | Albums | Documents | App-wise media
                                        - If you are NOT in Google Photos yet, you may use the device's app-opening action (e.g., open_app) to LAUNCH GOOGLE PHOTOS ONLY.
                                            Do NOT use it to open any other app.

                          Media collection (priority):
                          1) Follow these EXACT instructions to locate/select media on device: {media_instruction}
                        1a) CRITICAL: If opening Google Photos or any gallery app, SCROLL TO THE TOP first before looking for the media
                        - If you already selected media successfully earlier in this session, REUSE THAT SAME METHOD (Share → Modify) and re-select the SAME items; do not re-explore new flows
                          1b) PREFERRED MULTI-PHOTO METHOD (use before scrolling):
                              - Select the FIRST required photo
                              - Tap the "Share" button
                              - In the share sheet, tap "Modify" to add more photos
                              - In the modify view, select the remaining required photos
                              - Confirm selection, return to the share sheet, then choose X/Twitter
                              - This is the primary strategy; use scrolling only if Modify is unavailable
                          1c) SCROLL-BASED METHOD (fallback):
                              - Select ONE media first, then SCROLL from the MIDDLE OF THE SCREEN to find the NEXT media item
                                 * Scroll the media grid UPWARDS (swipe from bottom area towards top)
                                 * Start scroll gesture a little UPWARDS from the bottom of visible screen to avoid overlay issues
                              - Tap to add it to selection; repeat for each additional media
                              - Always scroll from the middle/center of the screen, NOT from edges
                              - Do it one by one; this is the fallback if Modify is not available
                          1d) MEDIA SELECTION STRATEGY:
                              - Image ordering in Photos and in-app "Add media" is NOT trustworthy - they may show different orders
                              - CRITICAL: You CANNOT select media separately and share them one by one to posting apps - must select all together
                              - CRITICAL: NEVER use X/Twitter's in-app media picker/gallery - it shows media from all sources in wrong order
                              - ALWAYS use Google Photos via share sheet - this ensures correct media selection
                              - If needed: collection/album view; different tabs; adjacent-image select/deselect/reselect
                    2) IMPORTANT: After selecting media, if you cannot find the share button or it's hidden behind a banner/overlay:
                       - Try swiping up slightly to reveal hidden UI elements
                       - Try tapping on empty space to dismiss any overlays or popups
                       - Look for share icons in corners or bottom of screen
                       - If needed, long-press on the media to get context menu with share option
                       - Scroll/swipe the thumbnail bar if the selected image seems hidden
                                        3) Use the system share sheet to share the selected media to X (com.twitter.android)
                                             so the X composer opens with the media already attached.
                                             SELECTION RULES (share sheet):
                                             - Choose the PLAIN tile labeled exactly "X" or "Twitter" (no subtitle under it)
                                             - DO NOT select tiles for "Direct Message", "Messages", or any DM options
                                             - If multiple plain tiles appear, prefer the one nearest top-left
                                             FALLBACK:
                                             - If tapping X/Twitter lands on the home feed instead of the composer:
                                                 * Press BACK twice quickly (within ~1s) to exit to the share sheet
                                                 * If a toast says "Tap again to exit", press BACK once more immediately
                                                 * If still in X/Twitter after two back presses: Press HOME, reopen Google Photos via open_app,
                                                     re-select media, open share sheet again, and select the plain X/Twitter tile

                          Compose and Post Tweet:
                          4) Confirm media thumbnails are visible in the composer BEFORE typing any text. If not, go back and re-share the media.
                          5) Call get_post_text() to retrieve THIS TWEET's text (tweet {chunk_num}/{total_chunks}, {len(chunk_text)} chars)
                          6) Store the returned text in a variable: tweet_content = get_post_text()
                              - The function will print "POST_TEXT: <actual text>"
                              - This printed text is what you MUST type
                          7) Type the ENTIRE returned text into the composer using: type(text=tweet_content, index=...)
                              - DO NOT type your own example text or placeholders
                              - DO NOT type test strings like "This is a test post..."
                              - ONLY use the variable tweet_content that contains the ACTUAL text
                          8) Look for and tap the "Post" or "Tweet" button
                          9) Wait for confirmation that the tweet was published
                          10) Return success status.

                    CRITICAL NOTES:
                    - get_post_text() returns ONLY THIS TWEET (tweet {chunk_num} of {total_chunks})
                    - This is part of a {total_chunks}-tweet thread
                    - DO NOT try to access or type other tweets - only THIS tweet
                          - You MUST use the exact text from get_post_text() - do NOT generate your own
                          - NEVER type hardcoded strings - ALWAYS use tweet_content
                          - You MUST publish the tweet - don't leave it as draft
                    
                    After posting:
                    9) Wait for confirmation that the tweet was published
                    10) Press HOME button (or swipe up from bottom) to return to Android home screen
                    11) Verify you're on the home screen before finishing
                    
                    Return success status and any confirmation info.
                    """
                else:
                    # Subsequent tweets (or first tweet without media): just post text
                    if chunk_idx == 0:
                        # First tweet without media
                        goal = f"""
                        CRITICAL: FOCUS ONLY ON X (TWITTER) - DO NOT OPEN ANY OTHER PLATFORMS
                        - You are ONLY posting to X (Twitter) right now
                        - DO NOT open Threads, Instagram, LinkedIn, or any other social media apps
                        - Complete this X (Twitter) task FULLY before finishing
                        - Return to home screen ONLY after X (Twitter) posting is complete
                        - If a prior media_selection_strategy is provided: {strategy_hint_text}
                        
                        Post to X (Twitter) (Tweet {chunk_num}/{total_chunks}):
                        
                        X COMPOSER LAYOUT:
                        - Compose button: BLUE PLUS icon in a blue circle, bottom-right, just above the bottom navigation bar
                        - Text input: Top of composer screen
                        - Attachment icons (below text): Media | GIF | Poll | Emoji | Schedule
                        - Post button: Top-right corner (says "Post")
                        - Bottom navigation: Home | Search | Grok AI (center) | Notifications | Inbox
                        
                        1. Open the X (Twitter) app (com.twitter.android)
                        2. Tap the BLUE PLUS button (bottom-right, above bottom nav) to open composer
                        3. Call get_post_text() to retrieve the tweet content ({len(chunk_text)} characters)
                        4. Store the returned text: tweet_content = get_post_text()
                        5. Type the ENTIRE returned text into the composer
                        6. Look for and tap the "Post" or "Tweet" button (usually at top right)
                        7. Wait for confirmation that the tweet was published
                        8. Return success status.

                        CRITICAL: The get_post_text() tool returns the ACTUAL tweet for this chunk.
                        You MUST use that exact text - do NOT generate your own text.
                        You MUST publish the tweet by tapping the Post button - don't leave it as draft.
                        
                        After posting:
                        8) Wait for confirmation that the tweet was published
                        9) Press HOME button (or swipe up from bottom) to return to Android home screen
                        10) Verify you're on the home screen before finishing
                        
                        Return success status and any confirmation info.
                        """
                    else:
                        # Reply/continuation tweet
                        goal = f"""
                        CRITICAL: FOCUS ONLY ON X (TWITTER) - DO NOT OPEN ANY OTHER PLATFORMS
                        - You are ONLY posting to X (Twitter) right now
                        - DO NOT open Threads, Instagram, LinkedIn, or any other social media apps
                        - Complete this X (Twitter) task FULLY before finishing
                        - Return to home screen ONLY after X (Twitter) posting is complete
                        
                        Reply to YOUR OWN previous tweet with the next part of the thread (Tweet {chunk_num}/{total_chunks}):
                        
                        CRITICAL: You MUST reply to YOUR OWN tweet, not someone else's tweet!
                        
                        X PROFILE AND REPLY LAYOUT:
                        - Profile button: Bottom navigation (usually Profile icon or your avatar)
                        - Your tweets: Shown in chronological order (most recent at top)
                        - Reply button: Located on YOUR tweet (usually bottom-left area of the tweet)
                        - Reply composer: Text input at top, Reply button at top-right
                        
                        STEP-BY-STEP PROCESS:
                        1. Go to YOUR PROFILE in X (Twitter):
                           - Tap your profile icon/avatar (usually bottom-right or in navigation)
                           - OR tap "Profile" in the bottom navigation
                           - Wait for your profile to load
                        2. Find YOUR MOST RECENT tweet (the one you just posted):
                           - Look at the TOP of your profile feed
                           - The MOST RECENT tweet is the FIRST one shown
                           - READ the tweet text to verify it matches the previous chunk you posted
                           - CRITICAL: Only reply to YOUR OWN tweet that you just posted
                        3. On YOUR tweet, look for the "Reply" button:
                           - Usually located at the bottom-left area of YOUR tweet
                           - May show as a reply icon (speech bubble) or "Reply" text
                           - CRITICAL: Make sure you're clicking Reply on YOUR tweet, not someone else's
                        4. Tap the Reply button on YOUR tweet to open the reply composer
                        5. Call get_post_text() to retrieve the tweet content for this chunk ({len(chunk_text)} characters)
                        6. Store the returned text: tweet_content = get_post_text()
                        7. Type the ENTIRE returned text into the reply composer
                        8. Look for and tap the "Reply" or "Post" button (usually top-right)
                        9. Wait for confirmation that the reply was published
                        10. Return success status.
                        
                        CRITICAL RULES:
                        - ALWAYS go to YOUR PROFILE first
                        - ALWAYS reply to YOUR MOST RECENT tweet
                        - DO NOT reply to someone else's tweet
                        - VERIFY the tweet text matches what you posted before replying
                        - If you can't find your tweet, scroll up on your profile to see the most recent ones

                        CRITICAL: The get_post_text() tool returns the ACTUAL tweet for this chunk.
                        You MUST use that exact text - do NOT generate your own text.
                        You MUST publish the reply by tapping the Reply/Post button - don't leave it as draft.
                        
                        After posting:
                        8) Wait for confirmation that the reply was published
                        9) If this is the last chunk, press HOME button (or swipe up from bottom) to return to Android home screen
                        10) Verify you're on the home screen before finishing (if last chunk)
                        
                        Return success status and any confirmation info.
                        """

                result = await self._run_droidrun_agent(goal, variables=agent_variables)

                if result["success"]:
                    posted_chunks += 1
                    logger.info(f"Tweet {chunk_num}/{total_chunks} posted successfully")
                else:
                    logger.warning(f"Tweet {chunk_num}/{total_chunks} failed: {result['reason']}")
                    # Continue trying to post remaining chunks even if one fails

            if posted_chunks > 0:
                logger.info(f"Twitter thread posted successfully ({posted_chunks}/{len(chunks)} tweets)")
                return PostResult(
                    platform="twitter",
                    success=True,
                    reason=f"Posted {posted_chunks}/{len(chunks)} tweets as a thread"
                )
            else:
                logger.warning("Failed to post any tweets to X")
                return PostResult(platform="twitter", success=False, reason="Failed to post any tweets")

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
        
        Write a SHORT, engaging description:
        - **Hook first:** Make the opening irresistible (curiosity, surprise, warmth, or delight)
        - **Be specific:** Avoid generic claims. If personal, make it relatable; if product/tech, make it clear
        - **Length:** MAXIMUM 60 characters - keep it SHORT and punchy
        - **Hashtags:** 0-2 relevant tags (optional, keep minimal)
        - **No thread:** Single tweet only, no follow-ups
        
        CONTENT TO TRANSFORM:
        {context}
        
        Respond with this JSON structure:
        {{
          "text": "Your short tweet (MAX 60 chars, hook first, authentic, specific)",
          "hashtags": ["#Tag1", "#Tag2"],
          "thread": []
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

        text = f"{name.title()} just dropped — quick and useful!"
        hashtags = ["#Tech", "#New"]
        thread = []

        return {
            "text": truncate_text(text, 60),
            "hashtags": hashtags,
            "thread": thread,
        }
