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

    def __init__(self, config: DroidrunConfig, timeout: int = 1500):
        super().__init__(config, "threads", timeout)
        self.post_max_length = 500  # Threads API limit is 500 characters per post
        self.chunk_cutoff = 400  # Start looking for sentence breaks at 20% before limit (500 * 0.8 = 400)
        self.hashtag_count = 3

    def _split_into_chunks(self, text: str, max_chunks: int = 20) -> List[str]:
        """
        Split text into chunks with max 500 characters (Threads limit), breaking at sentence boundaries.
        
        Strategy:
        - Start looking for sentence breaks at 400 chars (20% before 500 limit)
        - Each chunk must end with a sentence-ending punctuation mark
        - No text overlap between chunks
        - Each chunk is independent and complete
        """
        if not text or len(text) <= self.post_max_length:
            return [text]
        
        chunks = []
        remaining = text.strip()
        
        while remaining and len(chunks) < max_chunks:
            # If remaining text fits in one chunk, add it and done
            if len(remaining) <= self.post_max_length:
                chunks.append(remaining)
                break
            
            # Look for sentence break starting from 20% before max (400 chars for 500 limit)
            search_range = remaining[:self.chunk_cutoff + 100]  # Search window: 400-500 chars
            sentence_found = False
            
            # Try to find sentence endings, working backwards from the end
            for end_marker in ['. ', '? ', '! ', '.\n', '?\n', '!\n']:
                # Search in the window but prefer closer to the cutoff
                pos = search_range.rfind(end_marker)
                if pos > 200:  # Need at least 200 chars for meaningful chunk
                    end_pos = pos + 1  # Include the punctuation
                    chunk = remaining[:end_pos].strip()
                    if len(chunk) > 0:
                        chunks.append(chunk)
                        # Skip the punctuation and any following whitespace
                        remaining = remaining[end_pos:].lstrip()
                        sentence_found = True
                        break
            
            if sentence_found:
                continue
            
            # No sentence break found in window, try paragraph break
            para_pos = search_range.rfind('\n\n')
            if para_pos > 200:
                chunk = remaining[:para_pos].strip()
                chunks.append(chunk)
                remaining = remaining[para_pos:].strip()
                continue
            
            # Try line break
            line_pos = search_range.rfind('\n')
            if line_pos > 200:
                chunk = remaining[:line_pos].strip()
                chunks.append(chunk)
                remaining = remaining[line_pos:].strip()
                continue
            
            # Last resort: break at word boundary within window
            space_pos = search_range.rfind(' ')
            if space_pos > 200:
                chunk = remaining[:space_pos].strip()
                chunks.append(chunk)
                remaining = remaining[space_pos:].strip()
            else:
                # Force break at max length
                chunk = remaining[:self.post_max_length].strip()
                chunks.append(chunk)
                remaining = remaining[self.post_max_length:].strip()
        
        # Add any remaining text as final chunk
        if remaining and len(chunks) < max_chunks:
            chunks.append(remaining)
        
        return chunks if chunks else [text]

    async def _prepare_content(
        self,
        content: str | Dict[str, Any],
        context: Dict[str, Any],
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        try:
            # Extract text from content (handle both str and dict)
            if isinstance(content, dict):
                user_text = content.get("text", "")
                media_instructions = content.get("media_source_instructions", "")
            else:
                user_text = str(content) if content else ""
                media_instructions = context.get("media_source_instructions", "")
            
            # Also check context for media instructions
            if not media_instructions:
                media_instructions = context.get("media_source_instructions", "")
            
            logger.info(f"Threads prep: got text ({len(user_text)} chars), media_instructions={bool(media_instructions)}")
            
            # If we have actual user text (from transformed content), use it directly
            if user_text and len(user_text.strip()) > 10:
                logger.info(f"SUCCESS: Using provided text: {user_text[:100]}...")
                
                final_text = user_text.strip()
                # Keep full text for chunking in _post_to_platform
                if len(final_text) > self.post_max_length:
                    logger.warning(f"Text ({len(final_text)} chars) exceeds limit, will chunk during posting")
                
                prepared = {
                    "text": final_text,
                    "hashtags": [],
                    "thread": [],
                    "media_source_instructions": media_instructions
                }
                logger.info(f"SUCCESS: Prepared for Threads ({len(final_text)} chars)")
                prepared["media_selection_strategy"] = context.get("media_selection_strategy", "") if isinstance(context, dict) else ""
                return prepared
            
            # Only use agent if no text was provided
            logger.info("No text provided, running device agent for content generation...")
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

            # Get the prepared text
            base = prepared.get("text", "")
            
            # Ensure text respects Threads max (500 chars)
            # Keep full text for chunking in _post_to_platform
            if len(base) > self.post_max_length:
                logger.warning(f"WARNING: Prepared text ({len(base)} chars) exceeds Threads limit ({self.post_max_length} chars)")
                logger.info(f"Text will be chunked into multiple posts during posting phase")
                # Keep full text for chunking in _post_to_platform
                prepared["text"] = base
            else:
                prepared["text"] = base

            prepared["media_selection_strategy"] = context.get("media_selection_strategy", "") if isinstance(context, dict) else ""
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
            media_selection_strategy = prepared_content.get("media_selection_strategy", "")
            strategy_hint_text = media_selection_strategy or "Use Google Photos Share -> Modify; re-select the same items you picked previously; avoid exploring new flows."

            full_text = text
            if hashtags:
                full_text = f"{full_text}\n\n" + " ".join(hashtags)
            
            # Log the exact text being sent to the agent
            logger.info(f"POSTING TEXT TO THREADS ({len(full_text)} chars):")
            logger.info(f"{full_text}")
            
            # Split text into chunks with 500 char max, breaking at sentences
            chunks = self._split_into_chunks(full_text)
            logger.info(f"Split into {len(chunks)} chunks for threading")
            for i, chunk in enumerate(chunks, 1):
                logger.info(f"  Chunk {i} ({len(chunk)} chars): {chunk[:50]}...")
            
            all_media = list(set((media_urls or []) + (video_urls or [])))
            
            # Build goal: if media instructions provided, collect & share to Threads first
            thread_str = json.dumps(thread) if thread else "[]"

            # For threading, we need to handle each chunk separately
            logger.info(f"Prepared {len(chunks)} chunks for posting:")
            for i, chunk_text in enumerate(chunks, 1):
                logger.info(f"  Chunk {i}: {len(chunk_text)} chars - {chunk_text[:50]}...")
            
            posted_chunks = 0
            last_post_id = None
            
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
                    # First chunk with media: enforce media-first via share sheet
                    media_instruction = media_source_instructions.strip()
                    
                    goal = f"""
                    CRITICAL: FOCUS ONLY ON THREADS - DO NOT OPEN ANY OTHER PLATFORMS
                    - You are ONLY posting to Threads right now
                    - DO NOT open Twitter/X, Instagram, LinkedIn, or any other social media apps
                    - Complete this Threads task FULLY before finishing
                    - Return to home screen ONLY after Threads posting is complete
                    - If a prior media_selection_strategy is provided: {strategy_hint_text}
                    
                    Create a Threads post using media collected FIRST, then add text (Part {chunk_num}/{total_chunks}).

                    THREADS APP LAYOUT:
                    - POST button: BOTTOM CENTER of navigation bar
                    - Composer: Text input (top) | Attachment icons (horizontal row below)
                    - Attachment options (left to right): Gallery | GIF | Text | Quote | More
                    - Post/Share button: Top-right corner after composing

                    GOOGLE PHOTOS LAYOUT (when browsing for media):
                    - Top-left: Google Photos logo
                    - Top-right (3 icons, right to left): Profile | Notifications | New (plus icon)
                    - New button options: Create album | Collage | Highlight video | Cinematic | Animation | More
                    - Bottom panel (4 buttons): Photos | Collections | Create | Search
                    - CRITICAL: SCROLL TO THE TOP in Photos tab first to find media from most recent dates
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
                              - Confirm selection, return to the share sheet, then choose Threads
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
                              - CRITICAL: NEVER use Threads' in-app media picker/gallery - it shows media from all sources in wrong order
                              - ALWAYS use Google Photos via share sheet - this ensures correct media selection
                              - If needed: collection/album view; different tabs; adjacent-image select/deselect/reselect
                    2) IMPORTANT: After selecting media, if you cannot find the share button or it's hidden behind a banner/overlay:
                       - Try swiping up slightly to reveal hidden UI elements
                       - Try tapping on empty space to dismiss any overlays
                       - Look for share icons in corners or bottom of screen
                       - If needed, long-press on the media to get context menu with share option
                                                    3) Use the system share sheet to share the selected media to Threads (com.instagram.barcelona)
                                                            so the Threads composer opens with the media already attached.
                                                            SELECTION RULES (share sheet):
                                                            - Choose the PLAIN tile labeled exactly "Threads" (no subtitle under it)
                                                            - DO NOT select tiles for "Instagram" or any DM/Direct options
                                                            - If multiple plain "Threads" tiles appear, prefer the one nearest top-left
                                                            - If an option shows "threads ▾", select it and choose the appropriate composer INSIDE Threads
                                                            FALLBACK:
                                                            - If tapping Threads lands on the Threads home feed instead of the composer:
                                                                * Press BACK twice quickly (within ~1s) to exit to the share sheet
                                                                * If a toast says "Tap again to exit", press BACK once more immediately
                                                                * If still in Threads after two back presses: Press HOME, reopen Google Photos via open_app,
                                                                    re-select media, open share sheet again, and select the plain "Threads" tile
                                                            - CRITICAL: DO NOT TYPE ANY TEXT UNTIL YOU SEE THE MEDIA THUMBNAILS ATTACHED IN COMPOSER
                                                            - CRITICAL: If thumbnails are missing, GO BACK and re-share media before typing anything

                    Compose and Post in Threads:
                          4) Call get_post_text() to retrieve THIS CHUNK's text (chunk {chunk_num}/{total_chunks}, {len(chunk_text)} chars)
                          5) Store the returned text: post_content = get_post_text()
                              - The function will print "POST_TEXT: <actual text>"
                              - This printed text is what you MUST type
                          6) Type the ENTIRE returned text into the composer using: type(text=post_content, index=...)
                              - DO NOT type your own example text
                              - DO NOT type test strings like "This is a test post..."
                              - ONLY use the variable post_content that contains the ACTUAL text
                          7) Look for and tap the "Post" button
                    8) Wait for confirmation that the post was published
                    9) Return success status.

                    CRITICAL NOTES:
                    - get_post_text() returns ONLY THIS CHUNK (chunk {chunk_num} of {total_chunks})
                    - This is part of a {total_chunks}-post thread
                    - DO NOT try to access or type other chunks - only THIS chunk
                    - You MUST use the exact text from get_post_text() - do NOT generate your own
                                        - NEVER type hardcoded strings - ALWAYS use the variable post_content
                    - You MUST publish the post - don't leave it as draft
                    
                    After posting:
                    10) Wait for confirmation that the post was published
                    11) If this is the last chunk, press HOME button (or swipe up from bottom) to return to Android home screen
                    12) Verify you're on the home screen before finishing (if last chunk)
                    
                    Return success status and any confirmation info.
                    """
                else:
                    # Subsequent chunks (or first chunk without media): just post text
                    if chunk_idx == 0:
                        # First chunk without media
                        goal = f"""
                        CRITICAL: FOCUS ONLY ON THREADS - DO NOT OPEN ANY OTHER PLATFORMS
                        - You are ONLY posting to Threads right now
                        - DO NOT open Twitter/X, Instagram, LinkedIn, or any other social media apps
                        - Complete this Threads task FULLY before finishing
                        - Return to home screen ONLY after Threads posting is complete
                        
                        Post to Threads (Part {chunk_num}/{total_chunks}):
                        1. Open the Threads app
                        2. Tap the compose icon to create a new post
                        3. If media needs to be attached, do it NOW before typing any text. Confirm thumbnails are visible in the composer.
                        4. Call get_post_text() to retrieve THIS CHUNK's text (chunk {chunk_num}/{total_chunks}, {len(chunk_text)} chars)
                        5. Store the returned text in a variable: post_content = get_post_text()
                           - The function will print "POST_TEXT: <actual text>"
                           - This printed text is what you MUST type
                        6. Type the ENTIRE returned text into the composer using: type(text=post_content, index=...)
                           - DO NOT type your own example text
                           - DO NOT type test strings like "This is a test post..."
                           - ONLY use the variable post_content that contains the ACTUAL text
                           - NEVER type hardcoded strings - ALWAYS use the variable post_content
                        7. Look for and tap the "Post" button (usually at top right or bottom)
                        8. Wait for confirmation that the post was published
                        9. Return success status.

                        CRITICAL NOTES:
                        - get_post_text() returns ONLY THIS CHUNK (chunk {chunk_num} of {total_chunks})
                        - This is part of a {total_chunks}-post thread
                        - DO NOT try to access or type other chunks - only THIS chunk
                        - You MUST use the exact text from get_post_text() - do NOT generate your own
                        - You MUST publish the post by tapping the Post/Share button - don't leave it as draft
                        
                        After posting:
                        8) Wait for confirmation that the post was published
                        9) Press HOME button (or swipe up from bottom) to return to Android home screen
                        10) Verify you're on the home screen before finishing
                        
                        Return success status and any confirmation info.
                        """
                    else:
                        # Reply/continuation chunk
                        goal = f"""
                        CRITICAL: FOCUS ONLY ON THREADS - DO NOT OPEN ANY OTHER PLATFORMS
                        - You are ONLY posting to Threads right now
                        - DO NOT open Twitter/X, Instagram, LinkedIn, or any other social media apps
                        - Complete this Threads task FULLY before finishing
                        - Return to home screen ONLY after Threads posting is complete
                        
                        Reply to the previous Threads post with the next part of the thread (Part {chunk_num}/{total_chunks}):
                        
                        THREADS COMPOSER LAYOUT:
                        - POST button: BOTTOM CENTER of navigation bar to start new post
                        - Attachment options: Gallery | GIF | Text | Quote | More (horizontal row)
                        - Text input: Top of composer screen
                        - Publish button: Top-right corner
                        
                                1. Go to your profile and open the MOST RECENT post
                                2. READ the post content to confirm it matches the last chunk you posted
                                    - Only reply if the latest post content matches the current thread context
                                3. If it matches, look for a "Reply" button on that post and tap it to open the reply composer
                                4. If media needs to be attached to the reply, do it NOW before typing any text. Confirm thumbnails are visible in the composer.
                                5. Call get_post_text() to retrieve THIS CHUNK's text (chunk {chunk_num}/{total_chunks}, {len(chunk_text)} chars)
                                6. Store the returned text in a variable: post_content = get_post_text()
                                    - The function will print "POST_TEXT: <actual text>"
                                    - This printed text is what you MUST type
                                7. Type the ENTIRE returned text into the reply composer using: type(text=post_content, index=...)
                                    - DO NOT type your own example text
                                    - DO NOT type test strings like "This is a test post..."
                                    - ONLY use the variable post_content that contains the ACTUAL text
                                    - NEVER type hardcoded strings - ALWAYS use the variable post_content
                                8. Look for and tap the "Post" or "Reply" button
                                9. Wait for confirmation that the reply was published
                                10. Return success status.

                        CRITICAL NOTES:
                        - get_post_text() returns ONLY THIS CHUNK (chunk {chunk_num} of {total_chunks})
                        - This is a continuation/reply in a {total_chunks}-post thread
                        - DO NOT try to access or type other chunks - only THIS chunk
                        - You MUST use the exact text from get_post_text() - do NOT generate your own
                        - You MUST publish the reply by tapping the Post/Reply button - don't leave it as draft
                        
                        After posting:
                        8) Wait for confirmation that the reply was published
                        9) If this is the last chunk, press HOME button (or swipe up from bottom) to return to Android home screen
                        10) Verify you're on the home screen before finishing (if last chunk)
                        
                        Return success status and any confirmation info.
                        """

                result = await self._run_droidrun_agent(goal, variables=agent_variables)

                if result["success"]:
                    posted_chunks += 1
                    logger.info(f"Chunk {chunk_num}/{total_chunks} posted successfully")
                else:
                    logger.warning(f"Chunk {chunk_num}/{total_chunks} failed: {result['reason']}")
                    # Continue trying to post remaining chunks even if one fails

            if posted_chunks > 0:
                logger.info(f"Threads thread posted successfully ({posted_chunks}/{len(chunks)} chunks)")
                return PostResult(
                    platform="threads",
                    success=True,
                    reason=f"Posted {posted_chunks}/{len(chunks)} chunks as a thread"
                )
            else:
                logger.warning("Failed to post any chunks to Threads")
                return PostResult(platform="threads", success=False, reason="Failed to post any chunks")

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
