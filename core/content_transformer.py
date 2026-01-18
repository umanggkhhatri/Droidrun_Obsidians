"""
Transform raw content dumps into great Threads-worthy posts using Google Gemini.
"""

import asyncio
import os
import logging
from typing import Optional
from droidrun import DroidrunConfig

# Load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

async def transform_content_with_llm(
    content: str,
    config: Optional[DroidrunConfig] = None,
    model: str = "gemini-2.5-pro"
) -> str:
    if not content:
        logger.warning("Empty content provided, returning as-is")
        return content
    content = content.strip()
    if len(content) < 10:
        logger.debug(f"Content too short ({len(content)} chars), returning as-is")
        return content

    try:
        logger.info(f"🔄 Starting content transformation ({len(content)} chars)...")

        # Prefer the new google.genai SDK (google.generativeai is deprecated)
        try:
            from google import genai
        except ImportError:
            logger.error("❌ google-genai not installed! Install with: pip install google-genai")
            return content

        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("❌ No Google API key found! Set GOOGLE_API_KEY environment variable.")
            logger.error("   Run: export GOOGLE_API_KEY='your-api-key-here'")
            return content

        # Log that we found the key (mask it for security)
        masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        logger.info(f"✅ Using GOOGLE_API_KEY: {masked_key}")

        # Initialize client
        try:
            client = genai.Client(api_key=api_key)
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google GenAI client: {type(e).__name__}: {e}")
            return content

        prompt = f"""You are an expert social media content strategist specializing in Threads posts.

Transform the following raw content into an engaging, authentic Threads post.

CRITICAL INSTRUCTIONS:
- Your output will be posted DIRECTLY to Threads without any editing
- Return ONLY the final post text - NO explanations, NO commentary, NO meta-text
- Do NOT add phrases like "This is a test post" or "Here's the post:" or similar meta-commentary
- Just write the actual post content that users will see

REQUIREMENTS:
- LENGTH: 200-600 characters (this is important - make it substantial)
- TONE: Conversational and human, like texting a smart friend
- STRUCTURE: Hook opening → main insight → thought-provoking ending
- HASHTAGS: Include 2-3 relevant hashtags at the end if appropriate
- AUTHENTICITY: Write like a real person sharing genuine thoughts

CONTENT GUIDELINES:
- Start with an attention-grabbing hook or observation
- Include specific details, numbers, or examples from the source
- Share a unique perspective or insight
- End with a question, call-to-action, or memorable thought
- Be substantive - don't just summarize, add value

Source content to transform:
---
{content}
---

Write the transformed Threads post now (400-600 chars). Your response will be posted EXACTLY as written."""

        # Call LLM with timeout
        def _call_llm():
            return client.models.generate_content(
                model=model,
                contents=prompt,
            )

        response = await asyncio.wait_for(
            asyncio.to_thread(_call_llm),
            timeout=20.0
        )

        def _extract_text(resp):
            return (
                getattr(resp, "text", "")
                or getattr(resp, "candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                or ""
            )

        transformed = _extract_text(response)

        # If LLM echoes input, try a second pass with a stricter instruction
        if transformed and transformed.strip() == content:
            logger.info("ℹ️ LLM returned identical text; retrying with stronger rewrite instruction")
            def _call_llm_second_pass():
                stronger_prompt = prompt + "\n\nThe rewritten post MUST differ from the original wording and tighten to 300-450 chars."
                return client.models.generate_content(
                    model=model,
                    contents=stronger_prompt,
                )
            second = await asyncio.wait_for(
                asyncio.to_thread(_call_llm_second_pass),
                timeout=20.0
            )
            transformed = _extract_text(second)

        if not transformed:
            logger.warning("⚠️ LLM returned empty or invalid content, using original")
            return content

        transformed = transformed.strip()
        
        # Clean up any meta-commentary the LLM might have added
        cleanup_prefixes = [
            "Here's the transformed post:",
            "Here's the post:",
            "Here is the post:",
            "Transformed post:",
            "Post:",
        ]
        for prefix in cleanup_prefixes:
            if transformed.lower().startswith(prefix.lower()):
                transformed = transformed[len(prefix):].strip()
        
        if len(transformed) < 20:
            logger.warning("⚠️ LLM returned too-short content, using original")
            return content

        logger.info(f"✅ Content transformed successfully ({len(content)} → {len(transformed)} chars)")
        logger.info(f"📝 FINAL TRANSFORMED TEXT:\n{transformed}")
        return transformed

    except asyncio.TimeoutError:
        logger.error("⏱️ LLM transformation timed out after 20 seconds")
        return content
    except Exception as e:
        logger.error(f"❌ Error transforming content: {type(e).__name__}: {e}")
        return content
