"""Configuration settings for the social media agent system"""

from typing import Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Base configuration"""
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Agent timeouts (seconds)
    AGENT_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", "60"))
    CRAWL_TIMEOUT = int(os.getenv("CRAWL_TIMEOUT", "30"))
    
    # Content collection
    WHATSAPP_PHONE_NUMBER = os.getenv("WHATSAPP_PHONE_NUMBER", "9518185205")
    
    # Link crawling
    MAX_CRAWL_DEPTH = int(os.getenv("MAX_CRAWL_DEPTH", "2"))
    MAX_URLS_TO_CRAWL = int(os.getenv("MAX_URLS_TO_CRAWL", "5"))
    MAX_CHILD_URLS = int(os.getenv("MAX_CHILD_URLS", "2"))
    
    # Platform-specific settings
    PLATFORMS = {
        "instagram": {
            "enabled": os.getenv("INSTAGRAM_ENABLED", "false").lower() == "true",
            "timeout": int(os.getenv("INSTAGRAM_TIMEOUT", "60")),
            "caption_max_length": 2200,
        },
        "linkedin": {
            "enabled": os.getenv("LINKEDIN_ENABLED", "false").lower() == "true",
            "timeout": int(os.getenv("LINKEDIN_TIMEOUT", "60")),
            "post_max_length": 3000,
        },
        "twitter": {
            "enabled": os.getenv("TWITTER_ENABLED", "true").lower() == "true",
            "timeout": int(os.getenv("TWITTER_TIMEOUT", "60")),
            "tweet_max_length": 280,
        },
        "threads": {
            "enabled": os.getenv("THREADS_ENABLED", "false").lower() == "true",
            "timeout": int(os.getenv("THREADS_TIMEOUT", "60")),
            "post_max_length": 500,
        },
    }
    
    # Content adaptation settings
    INSTAGRAM_HASHTAG_COUNT = 20
    LINKEDIN_HASHTAG_COUNT = 15
    TWITTER_HASHTAG_COUNT = 5
    THREADS_HASHTAG_COUNT = 3
    
    # Retry settings
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY = int(os.getenv("RETRY_DELAY", "2"))  # seconds
    
    # Output
    SAVE_POSTS_TO_FILE = os.getenv("SAVE_POSTS_TO_FILE", "true").lower() == "true"
    POSTS_OUTPUT_DIR = os.getenv("POSTS_OUTPUT_DIR", "./output/posts")
    RESULTS_OUTPUT_DIR = os.getenv("RESULTS_OUTPUT_DIR", "./output/results")


class DevelopmentConfig(Config):
    """Development configuration"""
    LOG_LEVEL = "DEBUG"
    AGENT_TIMEOUT = 30
    MAX_CRAWL_DEPTH = 5


class ProductionConfig(Config):
    """Production configuration"""
    LOG_LEVEL = "WARNING"
    MAX_RETRIES = 5
    RETRY_DELAY = 5


class TestingConfig(Config):
    """Testing configuration"""
    LOG_LEVEL = "DEBUG"
    AGENT_TIMEOUT = 10
    MAX_CRAWL_DEPTH = 0
    SAVE_POSTS_TO_FILE = False


def get_config(env: str = None) -> Config:
    """
    Get configuration object based on environment
    
    Args:
        env: Environment name (development, production, testing)
             If None, uses APP_ENV environment variable or defaults to production
    
    Returns:
        Configuration object
    """
    if env is None:
        env = os.getenv("APP_ENV", "production").lower()
    
    configs = {
        "development": DevelopmentConfig,
        "production": ProductionConfig,
        "testing": TestingConfig,
    }
    
    config_class = configs.get(env, ProductionConfig)
    return config_class()
