# Architecture Documentation

## System Design

### Core Components

#### 1. Content Collector (`core/content_collector.py`)

**Purpose**: Extract content from WhatsApp chats

**Responsibilities**:

- Navigate WhatsApp app using DroidRun
- Extract all messages from specified chat
- Identify and extract URLs and media references
- Parse and structure collected data

**Key Methods**:

- `collect_from_whatsapp()`: Main collection method
- `_extract_urls_from_result()`: URL extraction from text

**Flow**:

```
WhatsApp App → DroidRun Agent → Message Extraction → URL Parsing → Content Object
```

---

#### 2. Link Crawler (`core/link_crawler.py`)

**Purpose**: Enrich content by crawling extracted URLs

**Responsibilities**:

- Recursively crawl URLs up to specified depth
- Extract relevant content from each page
- Filter URLs by domain to prevent external crawling
- Avoid duplicate crawling with visited set

**Key Methods**:

- `crawl_for_context()`: Main crawling orchestrator
- `_crawl_url_recursive()`: Recursive crawling logic
- `_fetch_url_content()`: Fetch individual URL

**Features**:

- Configurable depth (default: 2 levels)
- URL filtering and deduplication
- Timeout handling
- Error resilience

**Flow**:

```
URL List → Browser Navigation → Content Extraction → Child URL Detection → Recursive Crawl → Context Dict
```

---

#### 3. Base Platform Agent (`core/base_agent.py`)

**Purpose**: Abstract base for platform-specific agents

**Responsibilities**:

- Define common agent interface
- Handle DroidRun agent execution
- Provide retry logic with exponential backoff
- Manage timeouts and error handling
- JSON extraction utilities

**Key Methods**:

- `prepare_and_post()`: High-level workflow
- `_prepare_content()`: Abstract method for platform-specific prep
- `_post_to_platform()`: Abstract method for posting
- `_run_droidrun_agent()`: Execute DroidRun with timeout
- `_retry_operation()`: Retry with backoff

**Design Pattern**: Template Method

- Concrete agents override `_prepare_content()` and `_post_to_platform()`
- Common logic in base class
- Retry and error handling provided

---

#### 4. Platform-Specific Agents

Each agent extends `BasePlatformAgent` with platform-specific logic:

**InstagramAgent**

- Hashtag count: 20
- Caption limit: 2200 chars
- Focus: Flashy, visual, use-cases, emojis
- Output: Caption, hashtags, emojis, carousel ideas

**LinkedInAgent**

- Hashtag count: 15
- Post limit: 3000 chars
- Focus: Technical, professional, thought leadership
- Output: Headline, description, hashtags, CTA

**RedditAgent**

- Title limit: 300 chars
- Content limit: 40000 chars
- Focus: Community-appropriate, discussion starter
- Output: Title, content, tags, subreddit

**FacebookAgent**

- Hashtag count: 12
- Post limit: 63206 chars
- Focus: Broad appeal, shareable, accessible
- Output: Caption, description, hashtags

---

#### 5. Content Orchestrator (`core/orchestrator.py`)

**Purpose**: Coordinate entire workflow

**Responsibilities**:

- Manage component lifecycle
- Orchestrate sequential steps
- Track results and metrics
- Handle result persistence
- Provide comprehensive logging

**Workflow Steps**:

1. **Collect** - Extract from WhatsApp
2. **Crawl** - Enrich with context
3. **Post (Sequential)**:
   - Instagram (flashy)
   - LinkedIn (technical)
   - Reddit (community)
   - Facebook (broad appeal)

**Features**:

- Sequential posting (avoids rate limits)
- Retry delays between platforms
- Result aggregation
- File persistence
- Detailed reporting

---

### Data Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                        Main Execution                             │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Content Collector│
                    └──────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │ WhatsApp Chat     │
                    │ - Messages        │
                    │ - Links           │
                    │ - Media Refs      │
                    └─────────┬─────────┘
                              │
                              ▼ Content(text + URLs)
                    ┌──────────────────┐
                    │ Link Crawler     │
                    └──────────────────┘
                              │
                ┌─────────────┼─────────────┐
                ▼             ▼             ▼
            URL 1         URL 2         URL N
         (depth 0)      (depth 0)     (depth 0)
                │             │             │
         ┌──────▼─┐    ┌──────▼─┐    ┌──────▼─┐
         │Children│    │Children│    │Children│
         │(d=1)   │    │(d=1)   │    │(d=1)   │
         └────────┘    └────────┘    └────────┘
                │             │             │
                └─────────────┼─────────────┘
                              │
                              ▼ Context(URL→Content map)
                    ┌──────────────────────────┐
                    │ Platform Agents (Seq)    │
                    ├──────────────────────────┤
                    │ 1. Instagram             │
                    │ 2. LinkedIn              │
                    │ 3. Reddit                │
                    │ 4. Facebook              │
                    └──────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
        PostResult        PostResult        PostResult
        (success/fail)    (success/fail)    (success/fail)
            │                 │                 │
            └─────────────────┼─────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Result Reporting │
                    │ - Console        │
                    │ - File (JSON)    │
                    │ - Metrics        │
                    └──────────────────┘
```

---

### Class Hierarchy

```
BasePlatformAgent (abstract)
├── InstagramAgent
├── LinkedInAgent
├── RedditAgent
└── FacebookAgent

BaseModel (dataclass)
├── Content
├── PlatformPost
└── PostResult

Configuration
├── Config (base)
├── DevelopmentConfig
├── ProductionConfig
└── TestingConfig
```

---

### Dependency Injection

Components are initialized with dependencies:

```python
# In ContentOrchestrator.__init__
self.collector = ContentCollector(config, phone_number)
self.crawler = LinkCrawler(config, max_depth=2)
self.instagram_agent = InstagramAgent(config, timeout=60)

# All agents get same DroidrunConfig
# Easy to swap implementations or mock for testing
```

---

## Error Handling Strategy

### Levels

**1. Component Level**

- Try-catch in each component's main method
- Graceful degradation (return None/empty)
- Detailed logging

**2. Retry Level**

- Exponential backoff for DroidRun operations
- Configurable max retries
- Different delays for different operations

**3. Orchestrator Level**

- Step validation (check previous step success)
- Partial failure handling (continue if one platform fails)
- Result aggregation (show what succeeded)

### Example Flow

```
Operation → Timeout → Retry (delay 2s)
                       ├─ Success → Continue
                       ├─ Timeout → Retry (delay 4s)
                       │            ├─ Success → Continue
                       │            └─ Max retries → Log + Continue
                       └─ Other error → Log + Fallback
```

---

## Configuration Architecture

### Environment-Based

```
APP_ENV environment variable
    ↓
get_config(env) function
    ↓
├─ development: DevelopmentConfig (debug, short timeouts)
├─ production: ProductionConfig (warnings, standard timeouts)
└─ testing: TestingConfig (for automated tests)
    ↓
Platform-specific settings
├─ INSTAGRAM_ENABLED, INSTAGRAM_TIMEOUT
├─ LINKEDIN_ENABLED, LINKEDIN_TIMEOUT
├─ REDDIT_ENABLED, REDDIT_TIMEOUT
└─ FACEBOOK_ENABLED, FACEBOOK_TIMEOUT
```

### Configuration Hierarchy

1. **Default values** in Config class
2. **Environment variables** override defaults
3. **Runtime arguments** override environment
4. **Config instance** at runtime

```python
# Defaults
LOG_LEVEL = "INFO"

# Environment override
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")  # From .env or shell

# Runtime in get_config
if env == "development":
    config_class = DevelopmentConfig
    config.LOG_LEVEL = "DEBUG"
```

---

## Extensibility

### Adding New Platform

```python
# 1. Create agent
class NewPlatformAgent(BasePlatformAgent):
    async def _prepare_content(...):
        # Custom preparation

    async def _post_to_platform(...):
        # Custom posting

# 2. Register in orchestrator
self.newplatform_agent = NewPlatformAgent(config)

# 3. Add to workflow
platforms = [..., ("newplatform", self.newplatform_agent, "[5/6]")]
```

### Customizing Content Preparation

```python
class CustomInstagramAgent(InstagramAgent):
    async def _prepare_content(self, content, context, **kwargs):
        # Override behavior
        return custom_prepared_content
```

### Pluggable Components

All main components are injectable:

- ContentCollector can be swapped for another source
- LinkCrawler can use different crawling strategy
- Agents can be subclassed for custom behavior

---

## Performance Characteristics

### Time Complexity

- **Content Collection**: O(1) - Single chat extraction
- **URL Extraction**: O(n) - n = message count
- **Link Crawling**: O(n \* d) - n URLs, d depth levels
  - With 5 URLs, depth 2: ~10-20 pages
- **Content Preparation**: O(p) - p = number of platforms
- **Total**: Mostly I/O bound, not CPU bound

### Space Complexity

- **Content Storage**: O(n\*m) - n URLs, m average content per URL
- **Visited Set**: O(n) - tracking visited URLs
- **Results**: O(p) - results for p platforms

### Optimization Opportunities

- **Parallel Crawling**: Currently sequential, could be parallel
- **Caching**: Cache crawled URLs between runs
- **Batching**: Batch platform posts if supported
- **Content Compression**: Gzip content before storage

---

## Testing Strategy

### Unit Testing

- Mock DroidAgent for component tests
- Test each agent's content preparation
- Test URL extraction logic
- Test error handling

### Integration Testing

- Full workflow with mock content
- Verify data flow through orchestrator
- Test result persistence

### End-to-End Testing

- Use TestingConfig
- Run with actual device
- Verify all platforms receive content

---

## Deployment Considerations

### Requirements

- DroidRun framework installed
- Python 3.8+
- Mobile device with ADB
- Network connectivity
- .env configuration

### Monitoring

- Log levels by environment
- Result persistence for audit
- Error tracking
- Performance metrics

### Scaling

- Sequential posting is safe (no rate limit issues)
- Can run multiple instances for different numbers
- Results isolated to individual runs
- Stateless design allows horizontal scaling

---

## Security

### Data Handling

- WhatsApp messages processed locally
- No cloud storage of chat content
- URLs validated before crawling
- Results stored locally

### Permissions

- Requires device access via ADB
- App access depends on platform auth
- User responsible for account access

### Best Practices

- Use `.env` for secrets, never commit
- Validate all URLs before crawling
- Sanitize content before posting
- Review content before automatic posting
