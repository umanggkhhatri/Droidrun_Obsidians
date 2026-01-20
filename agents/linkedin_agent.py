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

    def __init__(self, config: DroidrunConfig, timeout: int = 1500):
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
                
                logger.info(f"Received text for posting ({len(user_text)} chars): {user_text[:150]}...")
                
                if user_text and len(user_text.strip()) > 10:
                    final_text = user_text.strip()
                    # Keep full text - will be handled in _post_to_platform
                    if len(final_text) > self.post_max_length:
                        logger.warning(f"Text ({len(final_text)} chars) exceeds limit, will truncate during posting")
                    
                    prepared = {
                        "headline": "",
                        "description": final_text,
                        "hashtags": [],
                        "cta": "",
                        "media_source_instructions": media_instructions
                    }
                    logger.info(f"SUCCESS: Prepared for LinkedIn ({len(final_text)} chars)")
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

            prepared["media_selection_strategy"] = context.get("media_selection_strategy", "") if isinstance(context, dict) else ""
            
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
            media_selection_strategy = prepared_content.get("media_selection_strategy", "")
            strategy_hint_text = media_selection_strategy or "Use Google Photos Share -> Modify; re-select the same items you picked previously; avoid exploring new flows."
            
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
            logger.info(f"POSTING TO LINKEDIN ({len(full_post)} chars):")
            logger.info(f"{full_post[:200]}...")
            
            all_media = list(set((media_urls or []) + (video_urls or [])))
            
            # Unified approach: post_chunks array (single item for LinkedIn)
            agent_variables = {
                "post_text": full_post,  # Required for get_post_text() tool
                "post_chunks": [full_post],  # Array with single chunk
                "current_chunk_index": 0,  # Always 0 for single post
                "current_chunk_number": 1,  # Always 1 for single post
                "total_chunks": 1,  # Always 1 for LinkedIn
            }
            # LinkedIn posting flow: Media-first via Google Photos share sheet to ensure attachments
            if media_source_instructions:
                media_instruction = media_source_instructions.strip()
                goal = f"""
                CRITICAL: FOCUS ONLY ON LINKEDIN - DO NOT OPEN ANY OTHER PLATFORMS
                - You are ONLY posting to LinkedIn right now
                - DO NOT open Twitter/X, Threads, Instagram, or any other social media apps
                - Complete this LinkedIn task FULLY before finishing
                - Return to home screen ONLY after LinkedIn posting is complete
                - If a prior media_selection_strategy is provided: {strategy_hint_text}

                MEDIA-FIRST VIA GOOGLE PHOTOS SHARE SHEET (required):
                - ALWAYS attach media before typing. Use Google Photos share sheet; do NOT rely on LinkedIn's in-app picker order.
                - If you already selected media successfully earlier in this session, REUSE THE SAME METHOD (Share → Modify) and pick the SAME items; avoid re-exploring new flows.

                GOOGLE PHOTOS LAYOUT:
                - Top-left: Google Photos logo
                - Bottom panel: Photos | Collections | Create | Search
                - CRITICAL: SCROLL TO THE TOP in Photos tab first to find recent media
                - If not in Photos, use open_app to launch com.google.android.apps.photos

                MEDIA SELECTION (priority):
                1) Follow these EXACT instructions to locate/select media on device: {media_instruction}
                   - CRITICAL: Read and follow the instruction PRECISELY - it tells you which specific media to select
                   - Do NOT select multiple items unless explicitly told to do so
                   - If instruction says "third picture" - select ONLY the third picture, not the first three
                   - If instruction says "second and fifth photos" - select ONLY those two, not all five
                2) Preferred multi-photo method (use first if selecting MULTIPLE items):
                    - Select the FIRST required photo
                    - Tap the "Share" button
                    - In the share sheet, tap "Modify" to add more photos
                    - In the modify view, select the remaining required photos
                    - Confirm selection, return to the share sheet
                3) Fallback scroll method (only if Modify unavailable):
                    - Select ONE media first, then scroll from the MIDDLE of the screen to find the next media item
                    - Tap to add it; repeat for each additional media
                4) Strategy notes:
                    - Image ordering in Photos and in-app pickers may differ; select all at once via Photos
                    - Do NOT try to share items one by one; select the full set together

                SHARE SHEET SELECTION (LinkedIn):
                - Choose the PLAIN tile labeled exactly "LinkedIn" (no subtitle). Avoid Messages/DM/Story variants.
                - If multiple plain tiles appear, prefer the one nearest top-left.
                - If tapping LinkedIn lands on the feed instead of the composer:
                  * Press BACK twice quickly (within ~1s) to return to the share sheet
                  * If still stuck, press HOME, reopen Photos via open_app, re-select media, and re-share to the plain LinkedIn tile

                Compose in LinkedIn (after share sheet):
                - Confirm media thumbnails are visible in the composer BEFORE typing. If missing, go BACK and re-share.
                - Call get_post_text() to retrieve the post content ({len(full_post)} characters)
                - Store it: post_content = get_post_text() (this printed text is what you type)
                - Type the ENTIRE returned text into the text input field (use only post_content)
                - Find and tap the "Post" button (typically TOP-RIGHT). Drafts are NOT acceptable; publish now.
                - If a Draft prompt appears, choose Post/Publish, not Save Draft.

                After posting:
                - Wait for confirmation (screen change or success toast)
                - Press HOME to return to Android home screen
                - Verify home screen, then finish

                Return success status and any confirmation info.
                """
            else:
                # No explicit media instructions provided
                goal = f"""
                CRITICAL: FOCUS ONLY ON LINKEDIN - DO NOT OPEN ANY OTHER PLATFORMS
                - You are ONLY posting to LinkedIn right now
                - DO NOT open Twitter/X, Threads, Instagram, or any other social media apps
                - Complete this LinkedIn task FULLY before finishing
                - Return to home screen ONLY after LinkedIn posting is complete

                MEDIA-FIRST VIA GOOGLE PHOTOS SHARE SHEET (required):
                - ALWAYS attach media before typing. Use Google Photos share sheet; do NOT rely on LinkedIn's in-app picker order.
                - If you already selected media successfully earlier in this session, REUSE THE SAME METHOD (Share → Modify) and pick the SAME items; avoid re-exploring new flows.

                GOOGLE PHOTOS LAYOUT:
                - Top-left: Google Photos logo
                - Bottom panel: Photos | Collections | Create | Search
                - CRITICAL: SCROLL TO THE TOP in Photos tab first to find recent media
                - If not in Photos, use open_app to launch com.google.android.apps.photos

                MEDIA SELECTION (priority):
                1) Preferred multi-photo method (use first):
                    - Select the FIRST required photo
                    - Tap the "Share" button
                    - In the share sheet, tap "Modify" to add more photos
                    - In the modify view, select the remaining required photos
                    - Confirm selection, return to the share sheet
                2) Fallback scroll method (only if Modify unavailable):
                    - Select ONE media first, then scroll from the MIDDLE of the screen to find the next media item
                    - Tap to add it; repeat for each additional media
                3) Strategy notes:
                    - Image ordering in Photos and in-app pickers may differ; select all at once via Photos
                    - Do NOT try to share items one by one; select the full set together

                SHARE SHEET SELECTION (LinkedIn):
                - Choose the PLAIN tile labeled exactly "LinkedIn" (no subtitle). Avoid Messages/DM/Story variants.
                - If multiple plain tiles appear, prefer the one nearest top-left.
                - If tapping LinkedIn lands on the feed instead of the composer:
                  * Press BACK twice quickly (within ~1s) to return to the share sheet
                  * If still stuck, press HOME, reopen Photos via open_app, re-select media, and re-share to the plain LinkedIn tile

                Compose in LinkedIn (after share sheet):
                - Confirm media thumbnails are visible in the composer BEFORE typing. If missing, go BACK and re-share.
                - Call get_post_text() to retrieve the post content ({len(full_post)} characters)
                - Store it: post_content = get_post_text() (this printed text is what you type)
                - Type the ENTIRE returned text into the text input field (use only post_content)
                - Find and tap the "Post" button (typically TOP-RIGHT). Drafts are NOT acceptable; publish now.
                - If a Draft prompt appears, choose Post/Publish, not Save Draft.

                After posting:
                - Wait for confirmation (screen change or success toast)
                - Press HOME to return to Android home screen
                - Verify home screen, then finish

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
            f"Excited to share {project}!\n\n"
            f"This represents a significant step forward in how we approach challenges "
            f"and deliver value. Looking forward to hearing your thoughts and feedback.\n\n"
            f"What opportunities do you see here? Let's connect and discuss!"
        )

        return {
            "headline": "",
            "description": truncate_text(description, self.post_max_length - 200),
            "hashtags": self._generate_default_hashtags(),
            "cta": "Share your thoughts in the comments!",
        }
