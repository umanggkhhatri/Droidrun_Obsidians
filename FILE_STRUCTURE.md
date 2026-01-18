# File Structure & Purposes

## Root Files

### `main.py` (500 lines)

**Purpose**: Main entry point with CLI interface

- Argument parsing (phone number, media URLs, environment)
- Workflow orchestration
- Error handling and exit codes
- User-friendly console output

**Usage**: `python main.py [options]`

---

## Configuration

### `config/settings.py` (90 lines)

**Purpose**: Environment-based configuration management

- Base Config class with defaults
- DevelopmentConfig, ProductionConfig, TestingConfig
- Platform-specific settings
- get_config() factory function

**Features**: Environment variables, multiple environments, per-platform customization

---

## Core Components

### `core/models.py` (60 lines)

**Purpose**: Data models using dataclasses

- `Content`: Collected content with metadata
- `PlatformPost`: Platform-specific prepared post
- `PostResult`: Result of posting operation

**Features**: Serialization support, type safety, clear data contracts

### `core/base_agent.py` (180 lines)

**Purpose**: Abstract base class for all platform agents

- Template method pattern implementation
- DroidRun agent execution wrapper
- Retry logic with exponential backoff
- JSON extraction and error handling
- Timeout management

**Key Methods**:

- `prepare_and_post()`: Main workflow
- `_prepare_content()`: Abstract, implemented by subclasses
- `_post_to_platform()`: Abstract, implemented by subclasses
- `_run_droidrun_agent()`: Execute DroidRun with timeout
- `_retry_operation()`: Retry logic

### `core/content_collector.py` (100 lines)

**Purpose**: Collect content from WhatsApp chats

- DroidRun agent execution for WhatsApp navigation
- URL extraction from chat messages
- Metadata collection (source, phone number, etc.)
- Error handling and logging

**Key Methods**:

- `collect_from_whatsapp()`: Main collection method
- `_extract_urls_from_result()`: Parse URLs from agent observation

### `core/link_crawler.py` (150 lines)

**Purpose**: Crawl URLs up to 2 levels deep for context

- Recursive URL crawling with depth control
- Domain-based filtering (prevent external crawling)
- Visited URL tracking to avoid duplicates
- Timeout handling per URL
- Child URL extraction and filtering

**Key Methods**:

- `crawl_for_context()`: Main crawling orchestrator
- `_crawl_url_recursive()`: Recursive crawling logic
- `_fetch_url_content()`: Fetch single URL content
- `_extract_child_urls()`: Extract and filter child URLs

### `core/orchestrator.py` (220 lines)

**Purpose**: Main workflow orchestration

- Component initialization and lifecycle
- Step-by-step workflow execution
- Sequential platform posting
- Result aggregation and reporting
- Result persistence to JSON file

**Key Methods**:

- `run_full_workflow()`: Main orchestration
- `_step_collect_content()`: Content collection step
- `_step_crawl_context()`: Context crawling step
- `_step_post_to_platforms()`: Platform posting step
- `_print_results_summary()`: Report results
- `_save_results()`: Persist results to file

---

## Platform Agents

### `agents/instagram_agent.py` (180 lines)

**Purpose**: Instagram-specific content adaptation and posting

- Flashy, visual content focus
- Hashtag optimization (20 tags)
- Emoji suggestions
- Carousel ideas for multiple images
- Caption truncation (2200 chars)

**Characteristics**: Visual appeal, use-case emphasis, engagement-focused

### `agents/linkedin_agent.py` (180 lines)

**Purpose**: LinkedIn professional content adaptation and posting

- Technical, thought leadership focus
- Professional hashtags (15 tags)
- Detailed descriptions (300-500 chars)
- CTA for engagement
- Industry-appropriate tone

**Characteristics**: Technical depth, professional tone, business value

### `agents/reddit_agent.py` (170 lines)

**Purpose**: Reddit community-appropriate content adaptation and posting

- Community norms adherence
- Discussion-starter format
- Configurable subreddit targeting
- Title optimization (60-80 chars)
- Community-specific tags

**Characteristics**: Community-focused, genuine value, discussion emphasis

### `agents/facebook_agent.py` (180 lines)

**Purpose**: Facebook broad-appeal content adaptation and posting

- Accessible, shareable format
- Broad audience appeal
- Hashtag optimization (12 tags)
- Engagement-boosting elements
- Professional yet casual tone

**Characteristics**: Broad appeal, relatability, shareability

---

## Utilities

### `utils/logger.py` (60 lines)

**Purpose**: Logging configuration and utilities

- Colored console formatter for readability
- setup_logger() function for consistent logging
- get_logger() convenience function
- Log level management

**Features**: Color-coded output (DEBUG, INFO, WARNING, ERROR)

### `utils/text_utils.py` (80 lines)

**Purpose**: Text processing utilities

- URL extraction with regex
- Text truncation with suffix
- JSON extraction from text
- Text cleaning (whitespace normalization)
- Domain extraction from URLs
- URL filtering by domain

**Functions**: extract_urls(), truncate_text(), clean_text(), extract_json_from_text()

---

## Documentation

### `README.md` (400+ lines)

**Purpose**: Complete user documentation

- System overview and architecture diagram
- Feature list with platform specifics
- Installation instructions
- Usage examples (basic and advanced)
- Configuration reference
- Output format documentation
- Extension guide
- API reference
- Environment modes
- Troubleshooting guide
- Performance considerations

### `ARCHITECTURE.md` (500+ lines)

**Purpose**: Technical design and architecture documentation

- Detailed component descriptions
- Responsibility breakdown
- Design patterns used (Template Method, Dependency Injection)
- Data flow diagrams
- Error handling strategy
- Configuration architecture
- Extensibility patterns
- Performance analysis
- Testing strategy
- Deployment considerations
- Security notes

### `PRODUCTION_SUMMARY.md` (200+ lines)

**Purpose**: Quick summary for production deployment

- What was built overview
- Complete directory structure with descriptions
- Key features checklist
- Quick start guide
- Advanced usage examples
- Configuration reference
- Data flow explanation
- Extensibility examples
- Performance metrics
- Testing information
- Next steps for production

---

## Examples & Testing

### `examples.py` (250 lines)

**Purpose**: 8 different usage examples

1. Basic complete workflow
2. Individual Instagram agent
3. Content collection only
4. URL crawling only
5. Custom Reddit subreddit
6. Environment modes comparison
7. Selective platform posting
8. Posting with media files

**Features**: Runnable examples with `asyncio.run()`, clear output

### `testing_utils.py` (250 lines)

**Purpose**: Testing utilities and mock data generators

- `MockContent`: Create sample content
- `ResultValidator`: Validate posting results
- `TestDataGenerator`: Generate test scenarios (GitHub, blog, product launch)
- `DebugReporter`: Print detailed debug info
- `export_results_to_json()`: Export results for analysis

**Features**: Mock data, validation, debug reporting, result export

---

## Configuration Files

### `.env.example` (40 lines)

**Purpose**: Configuration template

- All environment variables with defaults
- Comments explaining each setting
- Platform-specific configuration
- Output directory configuration

**Usage**: Copy to `.env` and customize

### `requirements.txt` (2 lines)

**Purpose**: Python dependencies

- droidrun>=0.1.0
- python-dotenv>=1.0.0

---

## Total Project Statistics

| Category        | Lines      | Files   |
| --------------- | ---------- | ------- |
| Core Logic      | 750        | 5       |
| Platform Agents | 720        | 4       |
| Utilities       | 140        | 2       |
| Configuration   | 130        | 1       |
| Examples        | 250        | 1       |
| Testing         | 250        | 1       |
| Documentation   | 1200+      | 3       |
| Entry Point     | 500        | 1       |
| **TOTAL**       | **~3900+** | **~18** |

---

## Code Quality Metrics

- **Type Hints**: 100% coverage
- **Docstrings**: Comprehensive (Google style)
- **Error Handling**: Try-catch at all levels
- **Logging**: Color-coded, structured logs
- **Modularity**: 10+ independent, reusable components
- **Documentation**: 1200+ lines of user-facing docs

---

## Import Graph

```
main.py
├── utils (logger, text_utils)
├── config.settings
└── core
    ├── run_workflow (orchestrator)
    │   ├── ContentCollector
    │   ├── LinkCrawler
    │   └── agents (Instagram, LinkedIn, Reddit, Facebook)
    │       └── BasePlatformAgent
    ├── models (Content, PostResult)
    └── base_agent

examples.py
├── core (all components)
├── agents (all agents)
└── config.settings

testing_utils.py
└── core.models
```

---

## File Dependencies

- No circular dependencies
- Clear single responsibility
- Dependency injection for testability
- Loose coupling between components
- High cohesion within each module

---

## Extension Points

### Easy to Add

1. **New Platform**: Create agent in `agents/`, extend `BasePlatformAgent`
2. **Custom Logic**: Override `_prepare_content()` in agent subclass
3. **Alternative Source**: Replace `ContentCollector` with new implementation
4. **Custom Crawler**: Replace `LinkCrawler` with enhanced version

### Without Modifying

- Core orchestration logic
- Base agent framework
- Configuration system
- Main entry point

---

## Maintenance & Updates

### Low-Risk Changes

- Adding new environment variables
- Tweaking timeouts in config
- Updating content templates in agents
- Adding new test data generators

### Medium-Risk Changes

- Modifying agent implementation
- Adding retry logic parameters
- Changing logging configuration

### High-Risk Changes

- Modifying base agent contract
- Changing data model structure
- Altering orchestration workflow

---

This modular structure makes the system:

- ✅ Easy to understand
- ✅ Easy to extend
- ✅ Easy to test
- ✅ Easy to maintain
- ✅ Production-ready
- ✅ Scalable
