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

    def __init__(self, config: DroidrunConfig, timeout: int = 400):
        super().__init__(config, "twitter", timeout)
        self.tweet_max_length = 280
        self.hashtag_count = 5
        self.chunk_size = 200  # Target size for tweet threads (stay well under 280)

    def _split_into_chunks(self, text: str, chunk_size: int = 200, max_chunks: int = 25) -> List[str]:
        """
        Split text into ~200 character chunks for tweet threads.
        
        Each chunk is independent and complete. Breaks at sentence boundaries.
        Stays under 280 char limit with good margin.
        """
        if not text or len(text) <= chunk_size:
            return [text]
        
        chunks = []
        remaining = text.strip()
        
        while remaining and len(chunks) < max_chunks:
            if len(remaining) <= chunk_size:
                chunks.append(remaining)
                break
            
            # For tweets, prioritize sentence breaks for readability
            safe_range = remaining[:chunk_size]
            sentence_found = False
            
            # Look for sentence endings
            for end_marker in ['. ', '? ', '! ', '.\n', '?\n', '!\n']:
                pos = safe_range.rfind(end_marker)
                if pos > 100:  # Need at least 100 chars for a good tweet
                    end_pos = pos + 1  # Include punctuation
                    chunk = remaining[:end_pos].strip()
                    chunks.append(chunk)
                    remaining = remaining[end_pos + len(end_marker) - 1:].strip()
                    sentence_found = True
                    break
            
            if sentence_found:
                continue
            
            # Try line break
            line_pos = safe_range.rfind('\n')
            if line_pos > 100:
                chunk = remaining[:line_pos].strip()
                chunks.append(chunk)
                remaining = remaining[line_pos:].strip()
                continue
            
            # Break at word boundary
            space_pos = safe_range.rfind(' ')
            if space_pos > 100:
                chunk = remaining[:space_pos].strip()
                chunks.append(chunk)
                remaining = remaining[space_pos:].strip()
            else:
                # Hard break as last resort
                chunk = remaining[:chunk_size].strip()
                chunks.append(chunk)
                remaining = remaining[chunk_size:].strip()
        
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
                
                logger.info(f"📝 Received text for posting ({len(user_text)} chars): {user_text[:150]}...")
                
                if user_text and len(user_text.strip()) > 10:
                    # Truncate to fit tweet limit
                    final_text = user_text.strip()
                    if len(final_text) > self.tweet_max_length - 30:  # Reserve space for hashtags
                        final_text = truncate_text(final_text, self.tweet_max_length - 30)
                    
                    prepared = {
                        "text": final_text,
                        "hashtags": [],
                        "thread": [],
                        "media_source_instructions": media_instructions
                    }
                    logger.info(f"✅ Prepared tweet for posting ({len(final_text)} chars)")
                else:
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
            if not text or len(text) < 40:
                prepared = self._fallback_prepare_content(content, context)

            # Normalize fields
            hashtags = prepared.get("hashtags", [])[: self.hashtag_count]
            hashtags = [tag if tag.startswith("#") else f"#{tag}" for tag in hashtags]
            prepared["hashtags"] = hashtags
            prepared.setdefault("thread", [])

            # Truncate tweet to fit including hashtags
            base = prepared.get("text", "")
            reserve = sum(len(h) + 1 for h in hashtags)
            trimmed = truncate_text(base, max(50, self.tweet_max_length - reserve - 1))
            prepared["text"] = trimmed

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

            full_text = text
            if hashtags:
                full_text = f"{full_text}\n\n" + " ".join(hashtags)
            
            # Log the exact text being sent to the agent
            logger.info(f"🎯 POSTING TWEET TO X ({len(full_text)} chars):")
            logger.info(f"📝 {full_text}")
            
            # Split text into ~200 character chunks for tweet threads
            chunks = self._split_into_chunks(full_text, chunk_size=self.chunk_size)
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
                
                # Pass text as variable (not embedded in goal string)
                agent_variables = {
                    "post_text": chunk_text,
                    "chunk_num": chunk_num,
                    "total_chunks": total_chunks,
                    "thread_items": thread,
                    "thread_items_json": thread_str
                }
                
                if chunk_idx == 0 and media_source_instructions:
                    # First tweet with media: enforce media-first via share sheet
                    media_instruction = media_source_instructions.strip()
                    
                    goal = f"""
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
                       - CRITICAL: NEVER use X/Twitter's in-app media picker/gallery - it shows media from all sources in wrong order
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
                    3) Use the system share sheet to share the selected media to X (com.twitter.android)
                       so the X composer opens with the media already attached.

                    Compose in X:
                    4) Call get_post_text() to retrieve the tweet content ({len(chunk_text)} characters)
                    5) Store the returned text in a variable: tweet_content = get_post_text()
                    6) Type the ENTIRE returned text into the composer using: type(text=tweet_content, index=...)
                    7) Look for and tap the "Post" or "Tweet" button (usually at top right)
                    8) Wait for confirmation that the tweet was published
                    9) Return success status.

                    CRITICAL: The get_post_text() tool returns the ACTUAL tweet for this chunk.
                    You MUST use that exact text - do NOT generate or summarize your own text.
                    You MUST publish the tweet by tapping the Post button - don't leave it as draft.
                    
                    Return success status and any confirmation info.
                    """
                else:
                    # Subsequent tweets (or first tweet without media): just post text
                    if chunk_idx == 0:
                        # First tweet without media
                        goal = f"""
                        Post to X (Twitter) (Tweet {chunk_num}/{total_chunks}):
                        
                        X COMPOSER LAYOUT:
                        - Compose button: BLUE PLUS icon (bottom-right of screen, above bottom navigation)
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
                        
                        Return success status and any confirmation info.
                        """
                    else:
                        # Reply/continuation tweet
                        goal = f"""
                        Reply to the previous tweet with the next part of the thread (Tweet {chunk_num}/{total_chunks}):
                        
                        X REPLY COMPOSER LAYOUT:
                        - Reply button: Located on the previous tweet (usually bottom-left area)
                        - Text input: Top of reply composer
                        - Attachment icons: Media | GIF | Poll | Emoji | Schedule (below text)
                        - Reply button: Top-right (says "Reply")
                        
                        1. Look for a "Reply" button or similar option on the last posted tweet
                        2. Tap to open the reply composer
                        3. Call get_post_text() to retrieve the tweet content for this chunk ({len(chunk_text)} characters)
                        4. Store the returned text: tweet_content = get_post_text()
                        5. Type the ENTIRE returned text into the reply composer
                        6. Look for and tap the "Reply" or "Post" button
                        7. Wait for confirmation that the reply was published
                        8. Return success status.

                        CRITICAL: The get_post_text() tool returns the ACTUAL tweet for this chunk.
                        You MUST use that exact text - do NOT generate your own text.
                        You MUST publish the reply by tapping the Reply/Post button - don't leave it as draft.
                        
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
