"""LinkedIn agent for posting formal, technical content"""

from typing import Dict, List, Optional, Any
import json
from urllib.parse import urlparse

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

    def __init__(self, config: DroidrunConfig, timeout: int = 400):
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
            content: Original content text or dict with text/media
            context: Crawled context data
            **kwargs: Additional arguments (unused)
        
        Returns:
            Dictionary with LinkedIn-specific content or None if failed
        """
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
                    final_text = user_text.strip()
                    if len(final_text) > self.post_max_length - 200:
                        final_text = truncate_text(final_text, self.post_max_length - 200)
                    
                    prepared = {
                        "headline": "",
                        "description": final_text,
                        "hashtags": self._generate_default_hashtags(),
                        "cta": "",
                        "media_source_instructions": media_instructions
                    }
                    logger.info(f"✅ Prepared post for LinkedIn ({len(final_text)} chars)")
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
            
            # Validate required fields with fallback
            if not prepared.get("description") or len(prepared.get("description", "")) < 40:
                logger.warning("Using fallback for LinkedIn content")
                prepared = self._fallback_prepare_content(content, context)
            
            if not prepared.get("headline"):
                prepared["headline"] = ""
            
            if not prepared.get("hashtags"):
                prepared["hashtags"] = []
            
            # Ensure hashtags are properly formatted
            prepared["hashtags"] = [
                tag if tag.startswith("#") else f"#{tag}"
                for tag in prepared["hashtags"][:self.hashtag_count]
            ]
            
            prepared.setdefault("cta", "")
            
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
            video_urls = prepared_content.get("videos", [])
            media_source_instructions = prepared_content.get("media_source_instructions", "")
            
            # Build full post content
            full_post = ""
            if headline:
                full_post = f"{headline}\n\n"
            full_post += description
            if hashtags:
                full_post += "\n\n" + " ".join(hashtags)
            if cta:
                full_post += f"\n\n{cta}"
            
            full_post = truncate_text(full_post, self.post_max_length)
            
            # Log the exact text being sent to the agent
            logger.info(f"🎯 POSTING TO LINKEDIN ({len(full_post)} chars):")
            logger.info(f"📝 {full_post[:200]}...")
            
            all_media = list(set((media_urls or []) + (video_urls or [])))
            
            # Pass post text as variable
            agent_variables = {
                "post_text": full_post,
            }
            
            if media_source_instructions:
                # Media path provided: enforce media-first via share sheet
                media_instruction = media_source_instructions.strip()
                
                goal = f"""
                Create a LinkedIn post using media collected FIRST, then add text.

                LINKEDIN COMPOSER LAYOUT:
                - POST button: CENTER of bottom navigation bar (plus icon)
                - Composer text input: Main area at top
                - Media attachment icons (bottom toolbar): Photo | Video | Document | Poll
                - Post button: Top-right corner (says "Post")
                - Audience selector: Top of composer (Who can see this)

                LINKEDIN APP LAYOUT:
                - Bottom navigation: Home | Network | POST (center plus icon) | Notifications | Jobs
                - Tap POST button (center of bottom nav) to create post
                - Post creation screen: Text area (top) | Media toolbar (bottom: photo, video, document)
                - Publish button: "Post" (top-right corner)

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
                   - CRITICAL: NEVER use LinkedIn's in-app media picker/gallery - it shows media from all sources in wrong order
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
                3) Use the system share sheet to share the selected media to LinkedIn (com.linkedin.android)
                   so the LinkedIn composer opens with the media already attached.

                Compose in LinkedIn:
                3) Call get_post_text() to retrieve the post content ({len(full_post)} characters)
                4) Store the returned text in a variable: post_content = get_post_text()
                5) Type the ENTIRE returned text into the post field using: type(text=post_content, index=...)
                6) Tap "Post" to publish.

                CRITICAL: The get_post_text() tool returns the ACTUAL post from the system.
                You MUST use that exact text - do NOT generate or summarize your own text.
                
                Return success status and any confirmation info.
                """
            else:
                # No media path: open LinkedIn directly
                media_str = f"Media URLs: {', '.join(all_media)}" if all_media else "No external media"
                
                goal = f"""
                Post to LinkedIn:
                
                LINKEDIN COMPOSER LAYOUT:
                - POST button: CENTER of bottom navigation bar (plus icon)
                - Text input: Top of composer screen
                - Media attachment icons (bottom): Photo | Video | Document | Poll
                - Audience selector: Top-left (Who can see this)
                - Post button: Top-right (says "Post")
                - Bottom navigation: Home | Network | POST (center) | Notifications | Jobs
                
                1. Open LinkedIn app (com.linkedin.android)
                2. Tap "Start a post" or the POST "+" button (center of bottom nav)
                3. Call get_post_text() to retrieve the post content ({len(full_post)} characters)
                4. Store the returned text: post_content = get_post_text()
                5. Type the ENTIRE returned text into the post field
                6. {f"Attach media from: {media_str}" if all_media else "No media to attach"}
                7. Tap "Post" to publish

                CRITICAL: The get_post_text() tool returns the ACTUAL post from the system.
                You MUST use that exact text - do NOT generate your own text.
                
                Return success status and any confirmation info.
                """
            
            result = await self._run_droidrun_agent(goal, variables=agent_variables)
            
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

    def _generate_default_hashtags(self) -> List[str]:
        """Generate default professional hashtags for LinkedIn"""
        return [
            "#innovation", "#technology", "#leadership", "#business",
            "#entrepreneurship", "#startup", "#growth", "#strategy",
            "#productivity", "#success", "#learning", "#motivation",
            "#networking", "#career", "#professional"
        ]

    def _fallback_prepare_content(self, content: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Build a professional post when LLM prep fails or content is sparse."""
        project = "this initiative"

        try:
            if isinstance(content, str) and content.startswith("http"):
                parsed = urlparse(content)
                slug = (parsed.path.strip("/") or parsed.netloc).split("/")[-1]
                if slug:
                    project = slug.replace("-", " ").replace("_", " ")
            elif isinstance(content, dict):
                text = content.get("text", "")
                if text:
                    project = text[:80]
        except Exception:
            pass

        description = (
            f"Excited to share {project}! 🚀\n\n"
            f"This represents a significant step forward in how we approach challenges "
            f"and deliver value. Looking forward to hearing your thoughts and feedback.\n\n"
            f"What opportunities do you see here? Let's connect and discuss!"
        )

        return {
            "headline": "",
            "description": truncate_text(description, self.post_max_length - 200),
            "hashtags": self._generate_default_hashtags(),
            "cta": "Share your thoughts in the comments! 👇",
        }
