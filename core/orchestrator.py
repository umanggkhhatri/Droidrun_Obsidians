"""Main orchestrator for the social media content posting workflow"""

import json
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import os

from droidrun import DroidrunConfig

from utils import get_logger, setup_logger
from config.settings import get_config
from core.models import Content, PostResult
from core.content_collector import ContentCollector
from core.link_crawler import LinkCrawler
from agents import InstagramAgent, LinkedInAgent, TwitterAgent, ThreadsAgent


logger = get_logger(__name__)


class ContentOrchestrator:
    """
    Main orchestrator for the complete workflow:
    1. Collect content from WhatsApp
    2. Crawl URLs for context
    3. Post to all platforms sequentially
    
    Manages:
    - Content collection and enrichment
    - Platform agent initialization
    - Sequential posting workflow
    - Result tracking and reporting
    """

    def __init__(self, config: DroidrunConfig, phone_number: str, app_config: Any = None):
        """
        Initialize orchestrator
        
        Args:
            config: DroidrunConfig instance
            phone_number: WhatsApp phone number to collect from
            app_config: Application configuration object
        """
        self.config = config
        self.phone_number = phone_number
        self.app_config = app_config or get_config()
        
        # Initialize components
        self.collector = ContentCollector(
            config, phone_number,
            timeout=self.app_config.AGENT_TIMEOUT
        )
        self.crawler = LinkCrawler(
            config,
            max_depth=self.app_config.MAX_CRAWL_DEPTH,
            max_urls=self.app_config.MAX_URLS_TO_CRAWL,
            timeout=self.app_config.CRAWL_TIMEOUT,
        )
        
        # Platform agents
        self.instagram_agent = InstagramAgent(
            config,
            timeout=self.app_config.PLATFORMS["instagram"]["timeout"]
        )
        self.linkedin_agent = LinkedInAgent(
            config,
            timeout=self.app_config.PLATFORMS["linkedin"]["timeout"]
        )
        self.twitter_agent = TwitterAgent(
            config,
            timeout=self.app_config.PLATFORMS["twitter"]["timeout"]
        )
        self.threads_agent = ThreadsAgent(
            config,
            timeout=self.app_config.PLATFORMS["threads"]["timeout"]
        )
        
        # Results tracking
        self.results: Dict[str, PostResult] = {}
        self.collected_content: Optional[Content] = None
        self.context_data: Dict[str, Any] = {}

    async def run_full_workflow(self, media_urls: List[str] = None) -> Dict[str, PostResult]:
        """
        Run the complete workflow from content collection to posting
        
        Args:
            media_urls: Optional list of media URLs to attach to posts
        
        Returns:
            Dictionary mapping platform names to PostResult objects
        """
        try:
            logger.info("=" * 60)
            logger.info("Starting Social Media Content Orchestration Workflow")
            logger.info("=" * 60)
            
            # Step 1: Collect content
            logger.info("\n[1/4] Collecting content from WhatsApp...")
            self.collected_content = await self._step_collect_content()
            if not self.collected_content:
                logger.error("Workflow failed: Unable to collect content")
                return {}
            
            # Step 2: Crawl for context
            logger.info("\n[2/4] Crawling URLs for context...")
            self.context_data = await self._step_crawl_context()
            logger.info(f"Context gathered from {len(self.context_data)} sources")
            
            # Step 3-6: Post to platforms sequentially
            await self._step_post_to_platforms(media_urls)
            
            # Final report
            logger.info("\n" + "=" * 60)
            logger.info("Workflow Complete - Final Results")
            logger.info("=" * 60)
            self._print_results_summary()
            
            # Save results if configured
            if self.app_config.SAVE_POSTS_TO_FILE:
                await self._save_results()
            
            return self.results
        
        except Exception as e:
            logger.error(f"Critical error in workflow: {str(e)}", exc_info=True)
            return {}

    async def _step_collect_content(self) -> Optional[Content]:
        """Step 1: Collect content from WhatsApp"""
        try:
            content = await self.collector.collect_from_whatsapp()
            if content:
                logger.info(f"✓ Content collected: {len(content.extracted_urls)} URLs found")
                logger.debug(f"  Original text length: {len(content.original_text)} chars")
            return content
        except Exception as e:
            logger.error(f"Failed to collect content: {str(e)}", exc_info=True)
            return None

    async def _step_crawl_context(self) -> Dict[str, Any]:
        """Step 2: Crawl URLs for context"""
        try:
            if not self.collected_content or not self.collected_content.extracted_urls:
                logger.warning("No URLs to crawl")
                return {}
            
            context = await self.crawler.crawl_for_context(
                self.collected_content.extracted_urls
            )
            logger.info(f"✓ Crawled {len(context)} URLs for context")
            return context
        except Exception as e:
            logger.error(f"Failed during crawling: {str(e)}", exc_info=True)
            return {}

    async def _step_post_to_platforms(self, media_urls: Optional[List[str]] = None) -> None:
        """Steps 3-6: Post to platforms sequentially"""
        if not self.collected_content:
            logger.error("No content to post")
            return
        
        # Pass complete content with media and videos
        content_dict = {
            "text": self.collected_content.original_text,
            "media": self.collected_content.media_files,
            "videos": self.collected_content.video_files,
            "urls": self.collected_content.extracted_urls,
        }
        
        # Platform posting sequence
        platforms = [
            ("twitter", self.twitter_agent, "[3/6]"),
            ("threads", self.threads_agent, "[4/6]"),
            ("instagram", self.instagram_agent, "[5/6]"),
            ("linkedin", self.linkedin_agent, "[6/6]"),
        ]
        
        for platform_name, agent, step_indicator in platforms:
            if not self.app_config.PLATFORMS[platform_name]["enabled"]:
                logger.info(f"\n{step_indicator} {platform_name.upper()} - Skipped (disabled)")
                self.results[platform_name] = PostResult(
                    platform=platform_name,
                    success=False,
                    reason="Platform disabled in configuration",
                )
                continue
            
            logger.info(f"\n{step_indicator} Posting to {platform_name.upper()}...")
            
            # Post to platform with complete content
            result = await agent.prepare_and_post(
                content_dict,
                self.context_data,
                media_urls=media_urls,
            )
            
            self.results[platform_name] = result
            
            status = "✓ Success" if result.success else "✗ Failed"
            logger.info(f"  {status}: {result.reason}")
            
            # Add small delay between platforms to avoid rate limiting
            if platform_name != platforms[-1][0]:  # Not last platform
                await asyncio.sleep(2)

    def _print_results_summary(self) -> None:
        """Print summary of posting results"""
        if not self.results:
            logger.warning("No results to display")
            return
        
        total = len(self.results)
        successful = sum(1 for r in self.results.values() if r.success)
        failed = total - successful
        
        logger.info(f"\nTotal: {total} | Success: {successful} | Failed: {failed}")
        logger.info("\nDetailed Results:")
        
        for platform, result in self.results.items():
            status_icon = "✓" if result.success else "✗"
            logger.info(f"  {status_icon} {platform.upper():10} - {result.reason}")
            if result.error:
                logger.debug(f"    Error: {result.error}")

    async def _save_results(self) -> None:
        """Save results to file"""
        try:
            output_dir = self.app_config.RESULTS_OUTPUT_DIR
            os.makedirs(output_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(output_dir, f"results_{timestamp}.json")
            
            results_data = {
                "timestamp": datetime.now().isoformat(),
                "phone_number": self.phone_number,
                "content_urls_collected": len(self.collected_content.extracted_urls) if self.collected_content else 0,
                "context_pages_crawled": len(self.context_data),
                "platform_results": [r.to_dict() for r in self.results.values()],
            }
            
            with open(filename, "w") as f:
                json.dump(results_data, f, indent=2)
            
            logger.info(f"\nResults saved to: {filename}")
        
        except Exception as e:
            logger.warning(f"Failed to save results: {str(e)}")


async def run_workflow(
    phone_number: str,
    droidrun_config: DroidrunConfig = None,
    app_config: Any = None,
    media_urls: List[str] = None,
) -> Dict[str, PostResult]:
    """
    Convenience function to run the complete workflow
    
    Args:
        phone_number: WhatsApp phone number to collect from
        droidrun_config: Optional DroidrunConfig (uses default if not provided)
        app_config: Optional application configuration
        media_urls: Optional media URLs to attach
    
    Returns:
        Dictionary of results by platform
    """
    droidrun_config = droidrun_config or DroidrunConfig()
    
    orchestrator = ContentOrchestrator(droidrun_config, phone_number, app_config)
    return await orchestrator.run_full_workflow(media_urls)
