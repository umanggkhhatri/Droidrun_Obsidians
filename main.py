"""
Social Media Content Posting Agent System

A modular, production-ready system for collecting content from WhatsApp,
enriching it through web crawling, and posting optimized content to multiple
social media platforms (Twitter/X, Threads, Instagram, LinkedIn) using DroidRun agents.

Usage:
    python main.py [--phone PHONE_NUMBER] [--media MEDIA_URL1 MEDIA_URL2 ...] [--env ENVIRONMENT]

Environment Variables:
    WHATSAPP_PHONE_NUMBER: Phone number to collect from (default: 9518185205)
    APP_ENV: Environment (development, production, testing)
    LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR)
    
Example:
    WHATSAPP_PHONE_NUMBER="+1234567890" python main.py
"""

import asyncio
import os
import argparse
from typing import List, Optional

from droidrun import DroidrunConfig

from utils import setup_logger
from config.settings import get_config
from core import run_workflow


logger = setup_logger(__name__)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Social Media Content Posting Agent System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default WhatsApp phone number from environment
  python main.py
  
  # Specify phone number and media URLs
  python main.py --phone "+1234567890" --media https://example.com/image1.jpg https://example.com/image2.jpg
  
  # Run in development mode with debug logging
  python main.py --env development
        """,
    )
    
    parser.add_argument(
        "--phone",
        type=str,
        default=None,
        help="WhatsApp phone number to collect content from",
    )
    
    parser.add_argument(
        "--media",
        type=str,
        nargs="*",
        default=None,
        help="Media URLs to attach to posts",
    )
    
    parser.add_argument(
        "--env",
        type=str,
        choices=["development", "production", "testing"],
        default=None,
        help="Environment to run in",
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without actually posting (preparation only)",
    )
    
    return parser.parse_args()


async def main():
    """Main entry point"""
    try:
        # Parse arguments
        args = parse_arguments()
        
        # Set environment if specified
        if args.env:
            os.environ["APP_ENV"] = args.env
        
        # Get configuration
        app_config = get_config(args.env)
        logger.info(f"Running in {app_config.__class__.__name__} mode")
        
        # Get phone number
        phone_number = args.phone or app_config.WHATSAPP_PHONE_NUMBER
        logger.info(f"Target WhatsApp chat: {phone_number}")
        
        # Get media URLs
        media_urls = args.media if args.media else None
        if media_urls:
            logger.info(f"Attaching {len(media_urls)} media files")
        
        # Initialize DroidRun config from YAML (required)
        cfg_path = os.path.join(os.path.expanduser("~"), ".droidrun", "config.yaml")
        if not os.path.exists(cfg_path):
            raise FileNotFoundError(
                f"Droidrun config.yaml not found at {cfg_path}.\n"
                f"Run 'droidrun setup' or ensure ~/.droidrun/config.yaml exists with valid LLM profiles and API keys."
            )
        
        try:
            droidrun_config = DroidrunConfig.from_yaml(cfg_path)
            logger.info(f"Loaded Droidrun config from {cfg_path}")
        except Exception as e:
            raise RuntimeError(
                f"Failed to load Droidrun config from {cfg_path}: {str(e)}\n"
                f"Ensure the YAML file is valid and contains required llm_profiles with valid API keys."
            )
        
        # Log dry-run mode if enabled
        if args.dry_run:
            logger.warning("Running in DRY-RUN mode - content will be prepared but NOT posted")
        
        # Run workflow
        logger.info("Starting workflow...")
        results = await run_workflow(
            phone_number=phone_number,
            droidrun_config=droidrun_config,
            app_config=app_config,
            media_urls=media_urls,
        )
        
        # Summary
        if results:
            successful = sum(1 for r in results.values() if r.success)
            failed = len(results) - successful
            logger.info(f"\nFinal Summary: {successful} successful, {failed} failed")
        else:
            logger.warning("No results returned from workflow")
        
        return 0
    
    except KeyboardInterrupt:
        logger.info("Workflow interrupted by user")
        return 130
    
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)