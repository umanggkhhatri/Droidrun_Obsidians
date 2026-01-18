# Social Media Content Posting Agent System

A production-ready, modular system for collecting content from WhatsApp, enriching it through intelligent web crawling, and posting platform-optimized content to Instagram, LinkedIn, Reddit, and Facebook using DroidRun mobile automation agents.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Main Orchestrator                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. Content Collector    2. Link Crawler      3. Platform Agents │
│  └─ WhatsApp Chat        └─ URL Extraction    ├─ Instagram      │
│     Message Extraction      Context Gathering  ├─ LinkedIn       │
│     Link Extraction         Recursive Crawl    ├─ Reddit         │
│     Media Detection         (2-level deep)     └─ Facebook       │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Features

### 🔄 Complete Workflow

- **Content Collection**: Extracts messages and links from WhatsApp chats
- **Context Enrichment**: Crawls URLs up to 2 levels deep for additional context
- **Multi-Platform Posting**: Sequentially posts to 4 major platforms
- **Platform Optimization**: Each agent adapts content for its platform

### 📱 Platform-Specific Agents

#### Instagram Agent

- **Focus**: Flashy, visually engaging content
- **Features**:
  - Catchy captions (150-200 chars)
  - 20+ relevant hashtags
  - Emoji suggestions
  - Carousel ideas for multi-image posts

#### LinkedIn Agent

- **Focus**: Professional, technical content
- **Features**:
  - Technical headlines
  - Detailed descriptions (300-500 chars)
  - 15 professional hashtags
  - Thought leadership tone

#### Reddit Agent

- **Focus**: Community-appropriate discussions
- **Features**:
  - Community-specific formatting
  - Discussion-starting titles (60-80 chars)
  - 10-15 subreddit-specific tags
  - Configurable subreddit targeting

#### Facebook Agent

- **Focus**: Broad appeal, shareable content
- **Features**:
  - Engaging captions
  - Accessible descriptions
  - 12 relevant hashtags
  - Engagement-boosting elements

### ⚙️ Production-Ready Features

- **Modular Architecture**: Each component is independent and reusable
- **Error Handling**: Comprehensive error handling and logging
- **Configuration Management**: Environment-based configuration
- **Retry Logic**: Exponential backoff for failed operations
- **Result Tracking**: Detailed logging and result persistence
- **CLI Interface**: Command-line arguments for flexibility

## Project Structure

```
.
├── main.py                 # Entry point
├── requirements.txt        # Dependencies
├── .env.example           # Configuration template
├── config/
│   └── settings.py        # Configuration management
├── core/
│   ├── __init__.py
│   ├── models.py          # Data models
│   ├── base_agent.py      # Abstract base agent
│   ├── content_collector.py # WhatsApp content collection
│   ├── link_crawler.py    # URL crawling
│   └── orchestrator.py    # Workflow orchestration
├── agents/
│   ├── __init__.py
│   ├── instagram_agent.py
│   ├── linkedin_agent.py
│   ├── reddit_agent.py
│   └── facebook_agent.py
└── utils/
    ├── __init__.py
    ├── logger.py          # Logging utilities
    └── text_utils.py      # Text processing utilities
```

## Installation

### Requirements

- Python 3.8+
- DroidRun framework
- Mobile device with ADB enabled

### Setup Steps

1. **Clone/Download Repository**

```bash
cd Droidrun_Obsidians
```

2. **Install Dependencies**

```bash
pip install -r requirements.txt
```

3. **Configure Environment**

```bash
cp .env.example .env
# Edit .env with your settings
```

4. **Verify DroidRun Installation**

```bash
python -c "from droidrun import DroidAgent; print('DroidRun ready')"
```

## Usage

### Basic Usage

```bash
# Use default configuration from .env
python main.py

# Specify phone number
python main.py --phone "+1234567890"

# Add media URLs
python main.py --phone "+1234567890" --media https://example.com/img1.jpg https://example.com/img2.jpg

# Run in development mode
python main.py --env development

# Dry run (prepare content without posting)
python main.py --dry-run
```

### Configuration

Edit `.env` file to customize:

```env
# Target WhatsApp contact
WHATSAPP_PHONE_NUMBER=+1234567890

# Environment mode
APP_ENV=production  # or development, testing

# Crawling depth (1-2 recommended)
MAX_CRAWL_DEPTH=2

# Platform enablement
INSTAGRAM_ENABLED=true
LINKEDIN_ENABLED=true
REDDIT_ENABLED=true
FACEBOOK_ENABLED=true

# Output settings
SAVE_POSTS_TO_FILE=true
RESULTS_OUTPUT_DIR=./output/results
```

### Advanced Usage

```python
from droidrun import DroidrunConfig
from core import run_workflow

async def custom_workflow():
    droidrun_config = DroidrunConfig()

    results = await run_workflow(
        phone_number="+1234567890",
        droidrun_config=droidrun_config,
        media_urls=["https://example.com/image.jpg"]
    )

    for platform, result in results.items():
        print(f"{platform}: {result.success}")
```

## Output

### Result Structure

Results are saved to `output/results/results_YYYYMMDD_HHMMSS.json`:

```json
{
  "timestamp": "2026-01-17T18:33:18",
  "phone_number": "+1234567890",
  "content_urls_collected": 5,
  "context_pages_crawled": 8,
  "platform_results": [
    {
      "platform": "instagram",
      "success": true,
      "reason": "Post published successfully",
      "post_id": null,
      "error": null,
      "timestamp": "2026-01-17T18:35:00"
    }
    // ... results for other platforms
  ]
}
```

### Log Output

Detailed logs with color coding:

```
[2026-01-17 18:33:18] INFO - core.orchestrator: Starting Social Media Content Orchestration Workflow
[2026-01-17 18:33:20] INFO - core.orchestrator: ✓ Content collected: 5 URLs found
[2026-01-17 18:33:45] INFO - core.orchestrator: ✓ Crawled 8 URLs for context
[2026-01-17 18:34:00] INFO - core.orchestrator: ✓ Success: Post published successfully
```

## Extension Guide

### Adding a New Platform

1. Create new agent file in `agents/`:

```python
# agents/tiktok_agent.py
from core import BasePlatformAgent

class TikTokAgent(BasePlatformAgent):
    async def _prepare_content(self, content, context, **kwargs):
        # Custom content preparation
        pass

    async def _post_to_platform(self, prepared_content, media_urls=None):
        # Custom posting logic
        pass
```

2. Add to orchestrator in `core/orchestrator.py`:

```python
from agents import TikTokAgent

self.tiktok_agent = TikTokAgent(config, timeout=60)
```

3. Add to platform posting sequence in `_step_post_to_platforms()`

### Customizing Content Preparation

Each agent's `_prepare_content` method can be overridden for custom behavior:

```python
class CustomInstagramAgent(InstagramAgent):
    async def _prepare_content(self, content, context, **kwargs):
        # Custom logic here
        return prepared_content
```

## API Reference

### ContentCollector

```python
collector = ContentCollector(config, phone_number, timeout=60)
content = await collector.collect_from_whatsapp()
# Returns: Content object with original_text, extracted_urls, etc.
```

### LinkCrawler

```python
crawler = LinkCrawler(config, max_depth=2, max_urls=5, timeout=30)
context = await crawler.crawl_for_context(urls)
# Returns: Dict[url, crawled_data]
```

### Platform Agents

```python
agent = InstagramAgent(config, timeout=60)
result = await agent.prepare_and_post(content, context, media_urls=None)
# Returns: PostResult with success status and details
```

### Orchestrator

```python
orchestrator = ContentOrchestrator(config, phone_number)
results = await orchestrator.run_full_workflow(media_urls=None)
# Returns: Dict[platform_name, PostResult]
```

## Environment Modes

### Development

- Debug logging enabled
- Shorter timeouts (10-30s)
- Single crawl depth
- Useful for testing

```bash
APP_ENV=development python main.py
```

### Production

- Warning+ logging
- Standard timeouts
- Full crawl depth
- Retry enabled
- Result persistence

```bash
APP_ENV=production python main.py
```

### Testing

- Debug logging
- Minimal crawling
- File output disabled
- For automated tests

```bash
APP_ENV=testing python main.py
```

## Troubleshooting

### Common Issues

**Content not collected**

- Verify WhatsApp is installed on device
- Check phone number format (+[country][number])
- Ensure chat exists with that contact

**Crawling fails**

- Check internet connectivity
- Verify URLs are accessible
- Reduce `MAX_CRAWL_DEPTH` if too slow

**Posts not publishing**

- Verify platform apps are installed
- Check account login status
- Review agent logs for specific errors
- Try `--dry-run` to test content preparation

### Debug Mode

Enable debug logging:

```bash
LOG_LEVEL=DEBUG python main.py
```

This will show:

- Agent decision-making process
- Detailed error messages
- URL extraction details
- Content transformation steps

## Performance Considerations

- **Crawling**: Average 5-10s per URL with 2-level depth
- **Content Preparation**: 10-30s per platform
- **Posting**: 20-60s per platform depending on media
- **Total Workflow**: 2-5 minutes for full cycle

Optimize with:

- Reduce `MAX_CRAWL_DEPTH`
- Lower `MAX_URLS_TO_CRAWL`
- Increase timeouts on slow connections

## License

Project by Umang Khhatri

## Contributing

Contributions welcome! Please follow:

- Modular design principles
- Type hints for all functions
- Comprehensive docstrings
- Error handling best practices

## Support

For issues or questions:

1. Check troubleshooting section
2. Review detailed logs with `--env development`
3. Check DroidRun documentation
4. Review agent-specific documentation in code
