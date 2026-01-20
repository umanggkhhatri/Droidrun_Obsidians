"""
Transform raw content dumps into great social media posts using Google Gemini.
Dynamic word limits based on content complexity and number of links.
"""

import asyncio
import os
import re
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


def _count_urls(content: str) -> int:
    """Count the number of URLs in the content."""
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    urls = re.findall(url_pattern, content)
    return len(set(urls))  # Unique URLs


def _calculate_char_limits(content: str) -> tuple[int, int]:
    """
    Calculate min/max character limits based on content.
    
    Base: 300-500 chars (no links, simple text)
    Per link: +300 chars (to include extracted details)
    Has crawled content marker: +200 chars
    
    Returns: (min_chars, max_chars)
    """
    num_urls = _count_urls(content)
    has_crawled = "CRAWLED LINK CONTENT:" in content or "=== MAIN PAGE:" in content
    
    # Base limits for simple text posts
    base_min = 300
    base_max = 500
    
    # Add chars per URL (to include extracted info)
    url_bonus = num_urls * 300
    
    # Bonus for having crawled content
    crawl_bonus = 400 if has_crawled else 0
    
    min_chars = base_min + (url_bonus // 2) + (crawl_bonus // 2)
    max_chars = base_max + url_bonus + crawl_bonus
    
    # Cap at reasonable limits
    min_chars = min(min_chars, 800)
    max_chars = min(max_chars, 2500)
    
    logger.info(f"Content analysis: {num_urls} URLs, crawled={has_crawled} → {min_chars}-{max_chars} chars")
    
    return min_chars, max_chars


async def transform_content_with_llm(
    content: str,
    config: Optional[DroidrunConfig] = None,
    model: str = "gemini-2.5-pro",
    platform: str = "general"
) -> str:
    if not content:
        logger.warning("Empty content provided, returning as-is")
        return content
    content = content.strip()
    if len(content) < 10:
        logger.debug(f"Content too short ({len(content)} chars), returning as-is")
        return content

    try:
        logger.info(f"Starting content transformation ({len(content)} chars)...")

        # Calculate dynamic character limits
        min_chars, max_chars = _calculate_char_limits(content)
        has_links = _count_urls(content) > 0
        has_crawled = "CRAWLED LINK CONTENT:" in content or "=== MAIN PAGE:" in content
        
        # Platform-specific tone and style
        platform_styles = {
            "threads": {
                "tone": "casual, conversational, authentic - like texting a friend",
                "style": "Start with 'honestly' or 'real talk' or jump right in. Use contractions. Ask rhetorical questions. Share personal takes. Sound HUMAN not AI.",
                "avoid": "formal language, corporate speak, 'dive into', 'delve', 'in conclusion', obvious AI phrases",
                "example_starters": "'ngl...', 'been thinking about...', 'ok but...', 'here's the thing...', 'so I found...'"
            },
            "twitter": {
                "tone": "punchy, direct, engaging - get to the point fast",
                "style": "Strong hook first line. Short sentences. Occasional fragments. Sound confident and natural. NO fluff.",
                "avoid": "'excited to share', 'thrilled to announce', corporate buzzwords, emoji overload",
                "example_starters": "'Just shipped...', 'Quick thread on...', 'Hot take:', 'Unpopular opinion:', 'PSA:'"
            },
            "instagram": {
                "tone": "visual storytelling, aspirational yet relatable",
                "style": "Focus on the visual/aesthetic. Use emojis tastefully. Short punchy sentences. Speak to benefits and experience.",
                "avoid": "walls of text, being too salesy, overusing hashtags in caption",
                "example_starters": "'Swipe for...', 'When you finally...', 'POV:', 'This is your sign to...'"
            },
            "linkedin": {
                "tone": "professional but approachable, thought leadership",
                "style": "Lead with insight. Share technical depth but explain clearly. Focus on learning/growth angle. Be authoritative yet humble.",
                "avoid": "too casual, humble brags, 'grateful' clichés, asking for engagement artificially",
                "example_starters": "'After building X, here's what I learned:', 'The problem with X:', 'Here's how we solved...'"
            },
            "general": {
                "tone": "professional yet conversational",
                "style": "Clear, engaging, informative",
                "avoid": "overly formal language, jargon without explanation",
                "example_starters": "standard openings"
            }
        }
        
        platform_info = platform_styles.get(platform.lower(), platform_styles["general"])

        # Prefer the new google.genai SDK (google.generativeai is deprecated)
        try:
            from google import genai
        except ImportError:
            logger.error("google-genai not installed! Install with: pip install google-genai")
            return content

        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("No Google API key found! Set GOOGLE_API_KEY environment variable.")
            logger.error("   Run: export GOOGLE_API_KEY='your-api-key-here'")
            return content

        # Log that we found the key (mask it for security)
        masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        logger.info(f"Using GOOGLE_API_KEY: {masked_key}")

        # Initialize client
        try:
            client = genai.Client(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to initialize Google GenAI client: {type(e).__name__}: {e}")
            return content

        # Build dynamic prompt based on content type
        if has_crawled:
            # Rich content with crawled data - comprehensive post
            content_instructions = """CONTENT SYNTHESIS REQUIREMENTS:
- Extract KEY INFORMATION from crawled content:
  • If it's a GitHub repo: summarize the architecture, tech stack, key features, what problem it solves
  • If it's a recipe: include key ingredients and important steps
  • If it's an article: summarize main points, insights, and takeaways
  • If it's a product: highlight features, benefits, and use cases
  • If it's documentation: explain the core concepts and how to get started
- COMBINE user's description with crawled data seamlessly
- Be SPECIFIC - include numbers, names, technologies, ingredients, etc.
- Include bullet points with emojis for key features/highlights"""
            
            structure = """STRUCTURE:
1. Opening hook that grabs attention
2. Main body with extracted details from the source
3. Key highlights as bullet points (use emojis like 🔹 ⚡ 🎯)
4. Your insight or why this matters
5. Call-to-action or closing thought
6. 3-5 relevant hashtags"""
        elif has_links:
            # Has links but no crawled content (crawling may have failed)
            content_instructions = """CONTENT REQUIREMENTS:
- Reference the linked content naturally
- Create engaging commentary about the topic
- Be conversational and add your perspective"""
            
            structure = """STRUCTURE:
1. Engaging opening hook
2. Your take on the topic
3. Why it matters or what's interesting
4. Call-to-action (check it out, thoughts?, etc.)
5. 2-3 relevant hashtags"""
        else:
            # Simple text post - no links
            content_instructions = """CONTENT REQUIREMENTS:
- Transform the text into an engaging social media post
- Keep it conversational and authentic
- Add personality and a clear point of view"""
            
            structure = """STRUCTURE:
1. Strong opening line
2. Main message or thought
3. Closing insight or question
4. 1-2 hashtags if appropriate"""

        prompt = f"""You are a social media content creator who writes like a REAL PERSON, not an AI.

PLATFORM: {platform.upper()}
TONE: {platform_info['tone']}
STYLE: {platform_info['style']}
AVOID: {platform_info['avoid']}
GOOD STARTERS: {platform_info['example_starters']}

CRITICAL - SOUND HUMAN:
- NO AI phrases: avoid "delve", "dive into", "navigate", "landscape", "in conclusion", "excited to share", "thrilled to"
- Use contractions (I'm, it's, won't, here's) 
- Write like you're texting or talking to someone
- Vary sentence length - mix short and long
- It's OK to start sentences with And, But, So, Or
- Use specific examples and concrete details
- Have a clear point of view or opinion
- Sound confident, not wishy-washy

YOUR OUTPUT RULES:
- Return ONLY the final post - NO meta-commentary
- Do NOT write "Here's the post:" or "Caption:" or any preamble
- Your response will be posted EXACTLY as written
- Length: {min_chars}-{max_chars} characters

{content_instructions}

{structure}

Source content to transform:
---
{content}
---

Write the post now as a REAL HUMAN would ({min_chars}-{max_chars} chars). No AI speak allowed."""

        # Call LLM with timeout
        def _call_llm():
            return client.models.generate_content(
                model=model,
                contents=prompt,
            )

        response = await asyncio.wait_for(
            asyncio.to_thread(_call_llm),
            timeout=45.0
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
            logger.info("LLM returned identical text; retrying with stronger rewrite instruction")
            def _call_llm_second_pass():
                stronger_prompt = prompt + "\n\nIMPORTANT: The post MUST be a complete rewrite with specific details extracted from the source. Include architecture details, key features, ingredients, or main points."
                return client.models.generate_content(
                    model=model,
                    contents=stronger_prompt,
                )
            second = await asyncio.wait_for(
                asyncio.to_thread(_call_llm_second_pass),
                timeout=45.0
            )
            transformed = _extract_text(second)

        if not transformed:
            logger.warning("LLM returned empty or invalid content, using original")
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
            logger.warning("LLM returned too-short content, using original")
            return content

        logger.info(f"Content transformed successfully ({len(content)} → {len(transformed)} chars)")
        logger.info(f"FINAL TRANSFORMED TEXT:\n{transformed}")
        return transformed

    except asyncio.TimeoutError:
        logger.error("LLM transformation timed out after 45 seconds")
        return content
    except Exception as e:
        logger.error(f"Error transforming content: {type(e).__name__}: {e}")
        return content
