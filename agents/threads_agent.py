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

    def __init__(self, config: DroidrunConfig, timeout: int = 400):
        super().__init__(config, "threads", timeout)
        self.post_max_length = 700  # Increased for longer, better posts
        self.hashtag_count = 3
        self.chunk_size = 425  # Target size for thread chunks (400-450 range)

    def _split_into_chunks(self, text: str, chunk_size: int = 425, max_chunks: int = 20) -> List[str]:
        """
        Split text into 400-450 character chunks for threading.
        
        Each chunk is a complete, independent unit - breaks at paragraph or sentence boundaries.
        No text overlap or repetition between chunks.
        """
        if not text or len(text) <= chunk_size:
            return [text]
        
        chunks = []
        remaining = text.strip()
        
        while remaining and len(chunks) < max_chunks:
            if len(remaining) <= chunk_size:
                chunks.append(remaining)
                break
            
            # First, try to break at paragraph boundaries (double newline)
            para_match = remaining[:chunk_size].rfind('\n\n')
            if para_match > 200:  # Good paragraph break
                chunk = remaining[:para_match].strip()
                chunks.append(chunk)
                remaining = remaining[para_match:].strip()  # Skip past the break
                continue
            
            # Try to find a sentence break within safe range (300-425 chars)
            # Look for sentence endings from the end backwards
            safe_range = remaining[:chunk_size]
            sentence_found = False
            
            for end_marker in ['. ', '? ', '! ', '.\n', '?\n', '!\n']:
                pos = safe_range.rfind(end_marker)
                if pos > 250:  # Only use if we get at least 250 chars
                    # Include the punctuation, exclude the space/newline after
                    end_pos = pos + 1  # Include the punctuation mark
                    chunk = remaining[:end_pos].strip()
                    chunks.append(chunk)
                    # Skip past the marker completely to avoid duplication
                    remaining = remaining[end_pos + len(end_marker) - 1:].strip()
                    sentence_found = True
                    break
            
            if sentence_found:
                continue
            
            # No sentence break found, try line break
            line_pos = safe_range.rfind('\n')
            if line_pos > 250:
                chunk = remaining[:line_pos].strip()
                chunks.append(chunk)
                remaining = remaining[line_pos:].strip()
                continue
            
            # Last resort: break at word boundary
            space_pos = safe_range.rfind(' ')
            if space_pos > 250:
                chunk = remaining[:space_pos].strip()
                chunks.append(chunk)
                remaining = remaining[space_pos:].strip()
            else:
                # Absolute last resort: hard break
                chunk = remaining[:chunk_size].strip()
                chunks.append(chunk)
                remaining = remaining[chunk_size:].strip()
        
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
            
            # Split text into 400-450 character chunks for threading
            chunks = self._split_into_chunks(full_text, chunk_size=self.chunk_size)
            logger.info(f"Split into {len(chunks)} chunks for threading")
            for i, chunk in enumerate(chunks, 1):
                logger.info(f"  Chunk {i} ({len(chunk)} chars): {chunk[:50]}...")
            
            all_media = list(set((media_urls or []) + (video_urls or [])))
            
            # Build goal: if media instructions provided, collect & share to Threads first
            thread_str = json.dumps(thread) if thread else "[]"

            # For threading, we need to handle each chunk separately
            # The agent will post each chunk and reply to it with the next chunk
            
            posted_chunks = 0
            last_post_id = None
            
            for chunk_idx, chunk_text in enumerate(chunks):
                chunk_num = chunk_idx + 1
                total_chunks = len(chunks)
                
                # Pass text and thread as variables (not embedded in goal string)
                # This ensures the agent uses the exact transformed text without reading/reinterpreting
                agent_variables = {
                    "post_text": chunk_text,
                    "chunk_num": chunk_num,
                    "total_chunks": total_chunks,
                    "thread_items": thread,
                    "thread_items_json": thread_str
                }
                
                if chunk_idx == 0 and media_source_instructions:
                    # First chunk with media: enforce media-first via share sheet
                    media_instruction = media_source_instructions.strip()
                    
                    goal = f"""
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
                       - CRITICAL: NEVER use Threads' in-app media picker/gallery - it shows media from all sources in wrong order
                       - ALWAYS use Google Photos via share sheet - this ensures correct media selection
                                             - If the scroll method above fails, try these alternative approaches:
                         * Select one image, then swipe up or down, then tap another image to add it to selection
                         * Try using the collection/album view if direct media browsing fails
                         * Try selecting from different tabs (Photos tab vs Collections tab)
                         * If a specific image won't select, try selecting adjacent images first, then deselect and reselect
                    2) IMPORTANT: After selecting media, if you cannot find the share button or it's hidden behind a banner/overlay:
                       - Try swiping up slightly to reveal hidden UI elements
                       - Try tapping on empty space to dismiss any overlays
                       - Look for share icons in corners or bottom of screen
                       - If needed, long-press on the media to get context menu with share option
                    3) Use the system share sheet to share the selected media to Threads (com.instagram.barcelona)
                       so the Threads composer opens with the media already attached.

                    Compose and Post in Threads:
                    4) Call get_post_text() to retrieve the post content ({len(chunk_text)} characters)
                    5) Store the returned text in a variable: post_content = get_post_text()
                    6) Type the ENTIRE returned text into the composer using: type(text=post_content, index=...)
                    7) Look for and tap the "Post" button (usually at top right or bottom)
                    8) Wait for confirmation that the post was published
                    9) Return success status.

                    CRITICAL: The get_post_text() tool returns the ACTUAL post content for this chunk.
                    You MUST use that exact text - do NOT generate or summarize your own text.
                    You MUST publish the post by tapping the Post/Share button - don't leave it as draft.
                    
                    Return success status and any confirmation info.
                    """
                else:
                    # Subsequent chunks (or first chunk without media): just post text
                    if chunk_idx == 0:
                        # First chunk without media
                        goal = f"""
                        Post to Threads (Part {chunk_num}/{total_chunks}):
                        1. Open the Threads app
                        2. Tap the compose icon to create a new post
                        3. Call get_post_text() to retrieve the post content ({len(chunk_text)} characters)
                        4. Store the returned text in a variable: post_content = get_post_text()
                        5. Type the ENTIRE returned text into the composer using: type(text=post_content, index=...)
                        6. Look for and tap the "Post" button (usually at top right or bottom)
                        7. Wait for confirmation that the post was published
                        8. Return success status.

                        CRITICAL: The get_post_text() tool returns the ACTUAL post content for this chunk.
                        You MUST use that exact text - do NOT generate or summarize your own text.
                        You MUST publish the post by tapping the Post/Share button - don't leave it as draft.
                        
                        Return success status and any confirmation info.
                        """
                    else:
                        # Reply/continuation chunk
                        goal = f"""
                        Reply to the previous Threads post with the next part of the thread (Part {chunk_num}/{total_chunks}):
                        
                        THREADS COMPOSER LAYOUT:
                        - POST button: BOTTOM CENTER of navigation bar to start new post
                        - Attachment options: Gallery | GIF | Text | Quote | More (horizontal row)
                        - Text input: Top of composer screen
                        - Publish button: Top-right corner
                        
                        1. Look for a "Reply" button or similar option on the last posted Threads post
                        2. Tap to open the reply composer
                        3. Call get_post_text() to retrieve the post content for this chunk ({len(chunk_text)} characters)
                        4. Store the returned text in a variable: post_content = get_post_text()
                        5. Type the ENTIRE returned text into the reply composer using: type(text=post_content, index=...)
                        6. Look for and tap the "Post" or "Reply" button
                        7. Wait for confirmation that the reply was published
                        8. Return success status.

                        CRITICAL: The get_post_text() tool returns the ACTUAL post content for this chunk.
                        You MUST use that exact text - do NOT generate or summarize your own text.
                        You MUST publish the reply by tapping the Post/Reply button - don't leave it as draft.
                        
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
