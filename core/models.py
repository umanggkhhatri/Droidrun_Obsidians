"""Data models for content orchestration system"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class Content:
    """Represents collected content from various sources"""
    original_text: str
    extracted_urls: List[str] = field(default_factory=list)
    media_files: List[str] = field(default_factory=list)
    video_files: List[str] = field(default_factory=list)
    context_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    collected_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "original_text": self.original_text,
            "extracted_urls": self.extracted_urls,
            "media_files": self.media_files,
            "video_files": self.video_files,
            "context_data": self.context_data,
            "metadata": self.metadata,
            "collected_at": self.collected_at.isoformat(),
        }


@dataclass
class PlatformPost:
    """Represents a post ready for a specific platform"""
    platform: str
    content: str
    media_urls: List[str] = field(default_factory=list)
    hashtags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    prepared_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "platform": self.platform,
            "content": self.content,
            "media_urls": self.media_urls,
            "hashtags": self.hashtags,
            "metadata": self.metadata,
            "prepared_at": self.prepared_at.isoformat(),
        }


@dataclass
class PostResult:
    """Result of a post operation"""
    platform: str
    success: bool
    reason: str
    post_id: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "platform": self.platform,
            "success": self.success,
            "reason": self.reason,
            "post_id": self.post_id,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }
