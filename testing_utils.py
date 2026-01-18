"""
Testing utilities for the social media agent system
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from core.models import Content, PostResult


"""Removed test utilities per user request."""
        
        print(f"\nOriginal Text ({len(content.original_text)} chars):")
        print(f"  {content.original_text[:200]}...")
        
        print(f"\nExtracted URLs ({len(content.extracted_urls)}):")
        for url in content.extracted_urls:
            print(f"  - {url}")
        
        print(f"\nContext Data:")
        for key, value in content.context_data.items():
            print(f"  {key}: {value}")
        
        print(f"\nMetadata:")
        for key, value in content.metadata.items():
            print(f"  {key}: {value}")
        
        print("-"*60 + "\n")
    
    @staticmethod
    def print_result_debug(result: PostResult) -> None:
        """Print detailed result debug info"""
        print("\n" + "-"*60)
        print(f"Result Debug Report - {result.platform.upper()}")
        print("-"*60)
        
        print(f"\nSuccess: {result.success}")
        print(f"Reason: {result.reason}")
        print(f"Post ID: {result.post_id}")
        print(f"Error: {result.error}")
        print(f"Timestamp: {result.timestamp}")
        
        print(f"\nMetadata:")
        for key, value in result.metadata.items():
            print(f"  {key}: {value}")
        
        print("-"*60 + "\n")
    
    @staticmethod
    def print_workflow_trace(
        content: Optional[Content],
        context: Dict[str, Any],
        results: Dict[str, PostResult],
    ) -> None:
        """Print complete workflow execution trace"""
        print("\n" + "="*60)
        print("Workflow Execution Trace")
        print("="*60)
        
        # Step 1: Collection
        print("\n[1] Content Collection")
        if content:
            print(f"  ✓ Collected {len(content.extracted_urls)} URLs")
            print(f"  ✓ Text: {len(content.original_text)} chars")
        else:
            print("  ✗ Failed to collect content")
        
        # Step 2: Crawling
        print("\n[2] URL Crawling")
        print(f"  ✓ Crawled {len(context)} pages")
        for url in list(context.keys())[:3]:
            print(f"    - {url}")
        if len(context) > 3:
            print(f"    ... and {len(context) - 3} more")
        
        # Step 3-6: Posting
        print("\n[3-6] Platform Posting")
        for platform, result in results.items():
            status = "✓" if result.success else "✗"
            print(f"  {status} {platform.upper():10} - {result.reason}")
        
        # Summary
        successful = sum(1 for r in results.values() if r.success)
        total = len(results)
        print(f"\nSummary: {successful}/{total} successful")
        print("="*60 + "\n")


def export_results_to_json(
    content: Content,
    context: Dict[str, Any],
    results: Dict[str, PostResult],
    filename: str = "test_results.json",
) -> None:
    """Export test results to JSON file"""
    data = {
        "timestamp": datetime.now().isoformat(),
        "content": {
            "text_length": len(content.original_text),
            "urls_count": len(content.extracted_urls),
            "urls": content.extracted_urls,
        },
        "context": {
            "pages_crawled": len(context),
            "urls": list(context.keys()),
        },
        "results": {
            platform: result.to_dict()
            for platform, result in results.items()
        },
        "summary": {
            "successful": sum(1 for r in results.values() if r.success),
            "failed": sum(1 for r in results.values() if not r.success),
            "total": len(results),
        },
    }
    
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"Results exported to {filename}")


if __name__ == "__main__":
    # Example usage of testing utilities
    print("Testing Utilities Available:")
    print("  - MockContent: Generate sample content")
    print("  - ResultValidator: Validate results")
    print("  - TestDataGenerator: Generate test scenarios")
    print("  - DebugReporter: Print detailed debug info")
    print("\nExample:")
    print("  from testing_utils import MockContent")
    print("  content = MockContent.create_sample_content()")
