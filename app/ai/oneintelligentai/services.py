"""
OneIntelligent AI Services
Business logic for conversation management, validation, and analytics
"""

import re
import html
import logging
from typing import List, Dict, Any, Optional, Tuple
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from django.db import models
from datetime import timedelta
from openai import AsyncOpenAI

# Try to import tiktoken, fallback to simple estimation if not available
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    tiktoken = None

from .models import Conversation, Message, ConversationAnalytics, UserPreferences

User = get_user_model()
logger = logging.getLogger("oneintelligent.ai")


class InputSanitizer:
    """Sanitizes and validates user input"""
    
    MAX_LENGTH = 10000
    MAX_MESSAGES = 100
    
    @staticmethod
    def sanitize_text(text: str) -> str:
        """Sanitize text input"""
        if not isinstance(text, str):
            return ""
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Trim whitespace
        text = text.strip()
        
        # Limit length
        if len(text) > InputSanitizer.MAX_LENGTH:
            text = text[:InputSanitizer.MAX_LENGTH]
            logger.warning(f"Input truncated from {len(text)} to {InputSanitizer.MAX_LENGTH}")
        
        return text
    
    @staticmethod
    def validate_content(content: Any) -> Tuple[bool, Optional[str]]:
        """Validate message content"""
        if not content:
            return False, "Content cannot be empty"
        
        if isinstance(content, str):
            if len(content) > InputSanitizer.MAX_LENGTH:
                return False, f"Content exceeds maximum length of {InputSanitizer.MAX_LENGTH} characters"
            # Check for potentially malicious patterns
            if re.search(r'<script|javascript:|onerror=|onload=', content, re.IGNORECASE):
                logger.warning("Potentially malicious content detected")
                return False, "Invalid content detected"
        
        return True, None
    
    @staticmethod
    def sanitize_messages(messages: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Sanitize and validate messages array"""
        if not isinstance(messages, list):
            return [], "Messages must be a list"
        
        if len(messages) == 0:
            return [], "At least one message is required"
        
        if len(messages) > InputSanitizer.MAX_MESSAGES:
            return [], f"Maximum {InputSanitizer.MAX_MESSAGES} messages allowed"
        
        sanitized = []
        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                return [], f"Message {i} must be a dictionary"
            
            role = msg.get("role", "").strip()
            if role not in ["user", "assistant", "system"]:
                return [], f"Invalid role '{role}' in message {i}"
            
            content = msg.get("content", "")
            is_valid, error = InputSanitizer.validate_content(content)
            if not is_valid:
                return [], f"Message {i}: {error}"
            
            # Sanitize string content
            if isinstance(content, str):
                content = InputSanitizer.sanitize_text(content)
            
            sanitized.append({
                "role": role,
                "content": content
            })
        
        return sanitized, None


class RateLimiter:
    """Rate limiting for AI requests"""
    
    RATE_LIMIT_KEY_PREFIX = "ai_rate_limit:"
    MAX_REQUESTS_PER_MINUTE = 30
    MAX_REQUESTS_PER_HOUR = 200
    MAX_REQUESTS_PER_DAY = 1000
    
    # In-memory fallback when Redis is unavailable
    _in_memory_cache: Dict[str, Dict[str, int]] = {}
    _cache_lock = None
    
    @staticmethod
    def _get_cache_value(key: str, default: int = 0) -> int:
        """Get value from cache with Redis fallback to in-memory"""
        try:
            return cache.get(key, default)
        except Exception as e:
            logger.warning(f"Redis cache unavailable, using in-memory fallback: {e}")
            # Fallback to in-memory cache
            if not hasattr(RateLimiter, '_in_memory_cache'):
                RateLimiter._in_memory_cache = {}
            return RateLimiter._in_memory_cache.get(key, default)
    
    @staticmethod
    def _set_cache_value(key: str, value: int, timeout: int):
        """Set value in cache with Redis fallback to in-memory"""
        try:
            cache.set(key, value, timeout)
        except Exception as e:
            logger.warning(f"Redis cache unavailable, using in-memory fallback: {e}")
            # Fallback to in-memory cache (no TTL in memory, but we'll clean up old keys)
            if not hasattr(RateLimiter, '_in_memory_cache'):
                RateLimiter._in_memory_cache = {}
            RateLimiter._in_memory_cache[key] = value
            # Simple cleanup: remove keys older than 1 day (approximate)
            if len(RateLimiter._in_memory_cache) > 1000:
                # Keep only recent keys (simple cleanup)
                keys_to_remove = list(RateLimiter._in_memory_cache.keys())[:-500]
                for k in keys_to_remove:
                    RateLimiter._in_memory_cache.pop(k, None)
    
    @staticmethod
    def check_rate_limit(user_id: str) -> Tuple[bool, Optional[str]]:
        """Check if user has exceeded rate limits"""
        now = timezone.now()
        
        # Per-minute limit
        minute_key = f"{RateLimiter.RATE_LIMIT_KEY_PREFIX}{user_id}:minute:{now.minute}"
        minute_count = RateLimiter._get_cache_value(minute_key, 0)
        if minute_count >= RateLimiter.MAX_REQUESTS_PER_MINUTE:
            return False, "Rate limit exceeded. Please wait a moment."
        
        # Per-hour limit
        hour_key = f"{RateLimiter.RATE_LIMIT_KEY_PREFIX}{user_id}:hour:{now.hour}"
        hour_count = RateLimiter._get_cache_value(hour_key, 0)
        if hour_count >= RateLimiter.MAX_REQUESTS_PER_HOUR:
            return False, "Hourly rate limit exceeded. Please try again later."
        
        # Per-day limit
        day_key = f"{RateLimiter.RATE_LIMIT_KEY_PREFIX}{user_id}:day:{now.date()}"
        day_count = RateLimiter._get_cache_value(day_key, 0)
        if day_count >= RateLimiter.MAX_REQUESTS_PER_DAY:
            return False, "Daily rate limit exceeded. Please try again tomorrow."
        
        return True, None
    
    @staticmethod
    def increment_rate_limit(user_id: str):
        """Increment rate limit counters"""
        now = timezone.now()
        
        # Per-minute
        minute_key = f"{RateLimiter.RATE_LIMIT_KEY_PREFIX}{user_id}:minute:{now.minute}"
        current_minute = RateLimiter._get_cache_value(minute_key, 0)
        RateLimiter._set_cache_value(minute_key, current_minute + 1, 120)  # 2 min TTL
        
        # Per-hour
        hour_key = f"{RateLimiter.RATE_LIMIT_KEY_PREFIX}{user_id}:hour:{now.hour}"
        current_hour = RateLimiter._get_cache_value(hour_key, 0)
        RateLimiter._set_cache_value(hour_key, current_hour + 1, 7200)  # 2 hour TTL
        
        # Per-day
        day_key = f"{RateLimiter.RATE_LIMIT_KEY_PREFIX}{user_id}:day:{now.date()}"
        current_day = RateLimiter._get_cache_value(day_key, 0)
        RateLimiter._set_cache_value(day_key, current_day + 1, 86400)  # 24 hour TTL


class TokenCounter:
    """Count tokens for messages"""
    
    @staticmethod
    def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
        """Count tokens in text"""
        if not text:
            return 0
        
        if TIKTOKEN_AVAILABLE and tiktoken:
            try:
                encoding = tiktoken.encoding_for_model(model)
                return len(encoding.encode(text))
            except Exception:
                # Fallback to estimation if model not found
                pass
        
        # Fallback: rough estimate (1 token ≈ 4 characters for English text)
        # This is a reasonable approximation for most cases
        return max(1, len(text) // 4)
    
    @staticmethod
    def count_message_tokens(message: Dict[str, Any], model: str = "gpt-4o-mini") -> int:
        """Count tokens in a message"""
        content = message.get("content", "")
        if isinstance(content, str):
            return TokenCounter.count_tokens(content, model)
        elif isinstance(content, list):
            # Handle multimodal content
            total = 0
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        total += TokenCounter.count_tokens(item.get("text", ""), model)
                    elif item.get("type") == "image_url":
                        # Rough estimate for images (varies by detail level)
                        total += 85  # Base cost for image
            return total
        return 0
    
    @staticmethod
    def count_conversation_tokens(messages: List[Dict[str, Any]], model: str = "gpt-4o-mini") -> int:
        """Count total tokens in conversation"""
        total = 0
        for msg in messages:
            total += TokenCounter.count_message_tokens(msg, model)
        return total


class ConversationManager:
    """Manages conversation persistence and retrieval"""
    
    @staticmethod
    def get_or_create_conversation(
        user: User,
        conversation_id: Optional[str] = None,
        mode: str = "Advisor",
        title: Optional[str] = None
    ) -> Conversation:
        """Get existing conversation or create new one"""
        if conversation_id:
            try:
                conv = Conversation.objects.get(
                    id=conversation_id,
                    user=user,
                    is_deleted=False
                )
                # Update last activity
                conv.last_activity_at = timezone.now()
                conv.save(update_fields=["last_activity_at"])
                return conv
            except Conversation.DoesNotExist:
                pass
        
        # Create new conversation
        conv = Conversation.objects.create(
            user=user,
            mode=mode,
            title=title or "New Conversation"
        )
        return conv
    
    @staticmethod
    def save_message(
        conversation: Conversation,
        role: str,
        content: str,
        tokens_used: int = 0,
        model_used: str = "",
        finish_reason: str = "",
        has_error: bool = False,
        error_message: str = ""
    ) -> Message:
        """Save a message to conversation"""
        # Get next sequence number
        last_message = Message.objects.filter(
            conversation=conversation
        ).order_by("-sequence").first()
        
        sequence = (last_message.sequence + 1) if last_message else 1
        
        message = Message.objects.create(
            conversation=conversation,
            role=role,
            content=content,
            tokens_used=tokens_used,
            model_used=model_used,
            finish_reason=finish_reason,
            has_error=has_error,
            error_message=error_message,
            sequence=sequence
        )
        
        # Update conversation metadata
        conversation.message_count = Message.objects.filter(
            conversation=conversation
        ).count()
        conversation.total_tokens += tokens_used
        conversation.last_activity_at = timezone.now()
        conversation.save(update_fields=[
            "message_count",
            "total_tokens",
            "last_activity_at"
        ])
        
        return message
    
    @staticmethod
    def load_conversation_messages(conversation: Conversation) -> List[Dict[str, Any]]:
        """Load messages from conversation as API format"""
        messages = Message.objects.filter(
            conversation=conversation
        ).order_by("sequence")
        
        return [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in messages
        ]
    
    @staticmethod
    def generate_title(user_message: str, mode: str) -> str:
        """Generate conversation title from first user message"""
        # Simple title generation (can be enhanced with AI)
        title = user_message[:50].strip()
        if len(user_message) > 50:
            title += "..."
        
        # Remove markdown and special characters
        title = re.sub(r'[#*`]', '', title)
        title = title.strip()
        
        return title or "New Conversation"


class AnalyticsTracker:
    """Tracks analytics for AI usage"""
    
    @staticmethod
    def track_request(
        user: User,
        conversation: Optional[Conversation],
        tokens_used: int,
        mode: str,
        response_time: float
    ):
        """Track a single request"""
        today = timezone.now().date()
        
        analytics, created = ConversationAnalytics.objects.get_or_create(
            user=user,
            date=today,
            mode_used=mode,
            defaults={
                "total_messages": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "avg_response_time": 0.0
            }
        )
        
        analytics.total_messages += 1
        analytics.total_tokens += tokens_used
        
        # Estimate cost (gpt-4o-mini: $0.15/$0.60 per 1M tokens)
        cost_per_1k_tokens = 0.00015  # Input
        estimated_cost = (tokens_used / 1000) * cost_per_1k_tokens
        analytics.total_cost += estimated_cost
        
        # Update average response time
        if analytics.avg_response_time == 0:
            analytics.avg_response_time = response_time
        else:
            analytics.avg_response_time = (
                (analytics.avg_response_time * (analytics.total_messages - 1) + response_time) /
                analytics.total_messages
            )
        
        analytics.save()
    
    @staticmethod
    def get_user_stats(user: User, days: int = 30) -> Dict[str, Any]:
        """Get user statistics"""
        since = timezone.now().date() - timedelta(days=days)
        
        analytics = ConversationAnalytics.objects.filter(
            user=user,
            date__gte=since
        ).aggregate(
            total_messages=models.Sum("total_messages"),
            total_tokens=models.Sum("total_tokens"),
            total_cost=models.Sum("total_cost"),
            avg_response_time=models.Avg("avg_response_time")
        )
        
        return {
            "total_messages": analytics.get("total_messages") or 0,
            "total_tokens": analytics.get("total_tokens") or 0,
            "total_cost": float(analytics.get("total_cost") or 0),
            "avg_response_time": float(analytics.get("avg_response_time") or 0),
            "period_days": days
        }


class PromptEnhancer:
    """Enhances prompts with better context and instructions"""
    
    @staticmethod
    def build_enhanced_context(
        user_data: Dict[str, Any],
        mode: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Build enhanced context with user information and history"""
        base_context = {
            "role": "system",
            "content": f"""
You are **Oneintelligent AI**, the AI companion designed to help users *Think, Act, and Grow Smarter & Faster.*

**User Context:**
- Name: {user_data.get('name', 'User')}
- Email: {user_data.get('email', '')}
- Current Mode: {mode}

**Your Mission:**
Help the user think more clearly, act more efficiently, and grow continuously. Provide insights, actionable guidance, and recommendations that drive real outcomes.

**Response Guidelines:**
1. Be concise but comprehensive
2. Provide actionable steps when applicable
3. Ask clarifying questions when needed
4. Suggest follow-up actions or learning opportunities
5. Use the STAR framework (Situation, Task, Action, Result, Recommendations) for complex topics

**Formatting:**
- Use GitHub-Flavored Markdown
- Numbered lists: `1. **Title** - Description` (single line)
- Headings: `### Heading Name` (not plain text with colons)
- Code blocks: ```language with proper tags
- Keep spacing tight (one blank line between sections)

**Mode-Specific Behavior:**
{mode} mode: Tailor your responses to {mode} context and needs.

Remember: Think, Act, Grow - Make every interaction valuable.
"""
        }
        
        return [base_context]

