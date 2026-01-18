"""
Examples demonstrating how to use the social media agent system
"""

import asyncio
from droidrun import DroidrunConfig

from core import (
    ContentCollector,
    LinkCrawler,
    ContentOrchestrator,
)
from agents import (
    InstagramAgent,
    LinkedInAgent,
    RedditAgent,
    FacebookAgent,
)
from config.settings import get_config


async def example_1_basic_workflow():
    """Example 1: Basic complete workflow"""
    print("\n" + "="*60)
    print("Example 1: Basic Complete Workflow")
    print("="*60)
    
    # Setup
    config = DroidrunConfig()
    phone_number = "+1234567890"
    
    # Run full workflow
    orchestrator = ContentOrchestrator(config, phone_number)
    results = await orchestrator.run_full_workflow()
    
    # Print results
    for platform, result in results.items():
        print(f"{platform}: {result.reason}")


async def example_2_individual_agent():
    """Example 2: Use individual platform agent directly"""
    print("\n" + "="*60)
    print("Example 2: Individual Instagram Agent")
    print("="*60)
    
    config = DroidrunConfig()
    app_config = get_config("development")
    
    # Create agent
    instagram = InstagramAgent(config, timeout=30)
    
    # Prepare and post
    sample_content = "Check out this amazing new Python framework!"
    sample_context = {
        "github_url": {
            "content": "Python framework for mobile automation..."
        }
    }
    sample_media = ["https://example.com/image1.jpg"]
    
    result = await instagram.prepare_and_post(
        sample_content,
        sample_context,
        media_urls=sample_media,
    )
    
    print(f"Status: {result.success}")
    print(f"Reason: {result.reason}")


async def example_3_content_collection_only():
    """Example 3: Just collect content without posting"""
    print("\n" + "="*60)
    print("Example 3: Content Collection Only")
    print("="*60)
    
    config = DroidrunConfig()
    phone_number = "+1234567890"
    
    # Collect content
    collector = ContentCollector(config, phone_number)
    content = await collector.collect_from_whatsapp()
    
    if content:
        print(f"Collected {len(content.extracted_urls)} URLs")
        print(f"Original text length: {len(content.original_text)} chars")
        print(f"URLs: {content.extracted_urls}")


async def example_4_url_crawling_only():
    """Example 4: Crawl URLs without posting"""
    print("\n" + "="*60)
    print("Example 4: URL Crawling Only")
    print("="*60)
    
    config = DroidrunConfig()
    
    # Sample URLs (in production these come from collector)
    urls = [
        "https://github.com/username/project",
        "https://blog.example.com/article",
    ]
    
    # Crawl for context
    crawler = LinkCrawler(config, max_depth=2)
    context = await crawler.crawl_for_context(urls)
    
    print(f"Crawled {len(context)} pages")
    for url, data in context.items():
        print(f"- {url}: {len(data['content'])} chars")


async def example_5_custom_reddit_subreddit():
    """Example 5: Post to specific Reddit subreddit"""
    print("\n" + "="*60)
    print("Example 5: Custom Reddit Subreddit")
    print("="*60)
    
    config = DroidrunConfig()
    
    # Create Reddit agent for specific subreddit
    reddit = RedditAgent(config, subreddit="Python")
    
    sample_content = "Released a new async Python library!"
    sample_context = {"project": "async-framework"}
    
    result = await reddit.prepare_and_post(
        sample_content,
        sample_context,
        subreddit="learnprogramming",  # Override default
    )
    
    print(f"Posted to: {result.reason}")


async def example_6_environment_modes():
    """Example 6: Using different environment modes"""
    print("\n" + "="*60)
    print("Example 6: Environment Modes")
    print("="*60)
    
    # Development mode - debug logging, short timeouts
    dev_config = get_config("development")
    print(f"Dev Mode - Log Level: {dev_config.LOG_LEVEL}, Timeout: {dev_config.AGENT_TIMEOUT}s")
    
    # Production mode - warning logging, longer timeouts
    prod_config = get_config("production")
    print(f"Prod Mode - Log Level: {prod_config.LOG_LEVEL}, Timeout: {prod_config.AGENT_TIMEOUT}s")
    
    # Testing mode - isolated, no file output
    test_config = get_config("testing")
    print(f"Test Mode - Log Level: {test_config.LOG_LEVEL}, File Output: {test_config.SAVE_POSTS_TO_FILE}")


async def example_7_selective_platforms():
    """Example 7: Enable/disable specific platforms"""
    print("\n" + "="*60)
    print("Example 7: Selective Platform Posting")
    print("="*60)
    
    config = DroidrunConfig()
    app_config = get_config("production")
    
    # Disable certain platforms
    app_config.PLATFORMS["facebook"]["enabled"] = False
    app_config.PLATFORMS["reddit"]["enabled"] = False
    
    print("Platforms enabled:")
    for platform, settings in app_config.PLATFORMS.items():
        if settings["enabled"]:
            print(f"  ✓ {platform}")
        else:
            print(f"  ✗ {platform}")
    
    # Now run workflow - only Instagram and LinkedIn will post
    orchestrator = ContentOrchestrator(config, "+1234567890", app_config)
    results = await orchestrator.run_full_workflow()
    
    for platform, result in results.items():
        print(f"{platform}: {result.reason}")


async def example_8_with_media():
    """Example 8: Post with media attachments"""
    print("\n" + "="*60)
    print("Example 8: Posting with Media")
    print("="*60)
    
    config = DroidrunConfig()
    
    media_urls = [
        "https://example.com/project_demo.mp4",
        "https://example.com/screenshot.png",
        "https://example.com/architecture.png",
    ]
    
    orchestrator = ContentOrchestrator(config, "+1234567890")
    results = await orchestrator.run_full_workflow(media_urls=media_urls)
    
    print(f"\nPosted with {len(media_urls)} media files")
    for platform, result in results.items():
        print(f"  {platform}: {result.reason}")


async def main():
    """Run all examples"""
    print("\n" + "="*80)
    print("Social Media Agent System - Usage Examples")
    print("="*80)
    
    # Uncomment to run specific examples
    
    # Example 1: Complete workflow
    # await example_1_basic_workflow()
    
    # Example 2: Single agent
    # await example_2_individual_agent()
    
    # Example 3: Content collection only
    # await example_3_content_collection_only()
    
    # Example 4: URL crawling only
    # await example_4_url_crawling_only()
    
    # Example 5: Custom Reddit subreddit
    # await example_5_custom_reddit_subreddit()
    
    # Example 6: Environment modes
    await example_6_environment_modes()
    
    # Example 7: Selective platforms
    # await example_7_selective_platforms()
    
    # Example 8: With media
    # await example_8_with_media()
    
    print("\n" + "="*80)
    print("Examples completed!")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
