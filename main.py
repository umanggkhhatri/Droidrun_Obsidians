"""
Social Media Content Posting Agent System (CLI - Deprecated)

Legacy CLI interface - use web interface (web/app.py) instead.
The web interface provides a modern UI with real-time progress tracking.

Usage:
    python -m web.app --port 5001

This CLI is kept for backward compatibility only.
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
        description="Social Media Content Posting Agent System (Deprecated - Use Web Interface)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run web interface (recommended)
  python -m web.app --port 5001
  
  # Run in development mode
  python main.py --env development
        """,
    )
    
    parser.add_argument(
        "--phone",
        type=str,
        default=None,
        help="Deprecated parameter (no longer used)",
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
        logger.warning("CLI mode is deprecated - use web interface: python -m web.app")
        
        # Get media URLs
        media_urls = args.media if args.media else None
        if media_urls:
            logger.info(f"Attaching {len(media_urls)} media files")
        
        # Initialize DroidRun config from YAML (required)
        cfg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "droidrun_config.yaml")
        if not os.path.exists(cfg_path):
            raise FileNotFoundError(
                f"Droidrun config.yaml not found at {cfg_path}.\n"
                f"Run 'droidrun setup' or ensure config/droidrun_config.yaml exists with valid LLM profiles and API keys."
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
        
        # Run workflow (deprecated - returns empty results)
        logger.info("Starting workflow...")
        logger.error("CLI workflow is no longer supported - use web interface")
        results = {}
        
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