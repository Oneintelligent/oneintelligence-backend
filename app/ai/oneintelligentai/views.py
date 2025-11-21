"""
OneIntelligent AI Backend API
Scalable, high-performance, secure AI chat endpoints
Aligned with enterprise-grade architecture
"""

import os
import json
import asyncio
import logging
import base64
import tempfile
import time
from typing import List, Dict, Any, Optional
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from openai import AsyncOpenAI
from openai import RateLimitError, APIError
from dotenv import load_dotenv
from asgiref.sync import async_to_sync, sync_to_async
from drf_spectacular.utils import extend_schema
from django.contrib.auth import get_user_model

from app.utils.response import api_response
from rest_framework import status as http_status
from app.platform.rbac.utils import has_module_permission, is_platform_admin
from app.platform.rbac.constants import Modules, Permissions
from app.platform.consent.utils import has_ai_consent
from .services import (
    InputSanitizer,
    RateLimiter,
    TokenCounter,
    ConversationManager,
    AnalyticsTracker,
    PromptEnhancer
)
from .models import Conversation

User = get_user_model()

load_dotenv()

# ============================================================
# CONFIGURATION
# ============================================================

logger = logging.getLogger("oneintelligent.ai")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

# OpenAI client (initialize with placeholder to avoid import errors)
# The actual API calls will check for valid key and return appropriate errors
openai_api_key = os.getenv("OPENAI_API_KEY", "sk-placeholder-not-configured")
try:
    client = AsyncOpenAI(api_key=openai_api_key)
    if openai_api_key in ["sk-placeholder-not-configured", "your-openai-api-key-here", ""]:
        logger.warning("OPENAI_API_KEY not properly configured. AI features will return errors until API key is set.")
except Exception as e:
    logger.error(f"Failed to initialize OpenAI client: {e}")
    client = None

# Model configuration
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MAX_MESSAGE_LENGTH = 10000
MAX_MESSAGES_PER_REQUEST = 100
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB

# ============================================================
# SYSTEM CONTEXT
# ============================================================

ONE_INTELLIGENT_CONTEXT = {
    "role": "system",
    "content": """
You are **Oneintelligent AI**, the AI companion of the One Intelligence workspace ecosystem (Project management, Task management, sales management, customer account management, customer support ticket management, internal chat all powered with oneintelligent ai to boost productivity by identifying the growth opportunities, risk, remind on pending items, etc— designed to help users *Think, Act, and Grow Smarter & Faster.*

### 🎯 Response Framework
Use the following structure **only when the user's question or task requires depth or reasoning**:
1. **Situation** — summarize the intent / situation in 3 lines.  
2. **Tasks** — Provide a clear, structured, list of tasks
3. **Action** — Describe how to accomplish the tasks. Keep the content with quality  
4. **Result** — Share the outcome, ensure the original ask is met, else be open to call out the situation.
5. **Recommendations** - Based on industry standards and best practices, recommend options to grow further.

### 💬 Tone & Behavior
- If the user greets (e.g., "hi", "hello", "thanks"), respond naturally and conversationally — no structured sections.  
- Be insightful, concise, and context-aware.  
- Tailor your tone to the user's role (developer, business, creative, etc.).  
- Always encourage better thinking, efficient action, and continuous growth.

### 📝 Formatting Guidelines
**CRITICAL: Always use strict GitHub-Flavored Markdown formatting. Follow these rules exactly:**

- **Numbered Lists**:
  - **MUST be formatted on a single line**: `1. United States` (NOT `1.` followed by a newline)
  - **Format**: `1. **Title**` for list items with headings
  - **Example**: `1. **United States** - The U.S. was the first country...`
  - **NEVER** put a newline after the number. Always keep the number, title, and description on the same line.
  - Use numbered lists (`1. First step`) for step-by-step instructions
  - Do NOT use colons after list item numbers
  
- **Headings**: 
  - Use `### Heading Name` for all section headings. NEVER use "Heading Name:" as plain text.
  - Examples: Use `### Step-by-Step Guide` NOT "Step-by-Step Guide:"
  - Do NOT repeat headings in the same response
  
- **Unordered Lists**: 
  - Use bullet points (`- Item` or `* Item`) for unordered lists
  
- **Code Blocks**: 
  - Always use code blocks with language tags: ```python, ```bash, ```yaml, etc.
  - Do NOT add "Copy" text or any metadata after code blocks
  
- **Sections**: 
  - Use `### Result` for result sections
  - Use `### Recommendations` for recommendations sections
  - Always use markdown headings, never plain text with colons
  
- **Spacing**: 
  - Use ONLY one blank line between sections
  - Do NOT add extra blank lines anywhere
  - Keep structure tight and valid markdown

Stay aligned with your mission: **Think, Act, and Grow Faster & Smarter.**
"""
}

# ============================================================
# VALIDATION & SECURITY
# ============================================================

def validate_user_data(user_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """Validate user data from request"""
    if not user_data:
        return False, "User data is required"
    
    required_fields = ["id", "email", "name"]
    for field in required_fields:
        if not user_data.get(field):
            return False, f"User {field} is required"
    
    return True, None

def validate_messages(messages: List[Dict[str, Any]]) -> tuple[bool, Optional[str]]:
    """Validate messages array"""
    if not isinstance(messages, list):
        return False, "Messages must be a list"
    
    if len(messages) == 0:
        return False, "At least one message is required"
    
    if len(messages) > MAX_MESSAGES_PER_REQUEST:
        return False, f"Maximum {MAX_MESSAGES_PER_REQUEST} messages allowed per request"
    
    for msg in messages:
        if not isinstance(msg, dict):
            return False, "Each message must be a dictionary"
        
        if "role" not in msg or "content" not in msg:
            return False, "Each message must have 'role' and 'content'"
        
        if msg["role"] not in ["user", "assistant", "system"]:
            return False, f"Invalid role: {msg['role']}"
        
        content = msg.get("content", "")
        if isinstance(content, str) and len(content) > MAX_MESSAGE_LENGTH:
            return False, f"Message content exceeds maximum length of {MAX_MESSAGE_LENGTH} characters"
    
    return True, None

def validate_mode(mode: str) -> tuple[bool, Optional[str]]:
    """Validate AI mode"""
    valid_modes = [
        "Advisor", "Developer", "Researcher", "Learner",
        "Sales", "Marketing", "Customer Support", "Task Manager"
    ]
    if mode not in valid_modes:
        return False, f"Invalid mode. Must be one of: {', '.join(valid_modes)}"
    return True, None

def build_user_context(user_data: Dict[str, Any], mode: str) -> Dict[str, str]:
    """Build user context for system prompt"""
    return {
        "role": "system",
        "content": f"""
User Information:
- ID: {user_data.get('id')}
- Name: {user_data.get('name')}
- Email: {user_data.get('email')}
- Current Mode: {mode}

Provide responses tailored to the {mode} mode and user's context.
"""
    }

# ============================================================
# STREAMING HELPERS
# ============================================================

async def stream_openai_response_sse(
    conversation: List[Dict[str, Any]],
    model_name: str = DEFAULT_MODEL
):
    """
    Async generator to yield OpenAI streaming responses
    formatted as Server-Sent Events (SSE).
    Optimized for performance and error handling.
    """
    try:
        # Check if OpenAI API key is properly configured
        openai_api_key = os.getenv("OPENAI_API_KEY", "")
        if not openai_api_key or openai_api_key in ["sk-placeholder-not-configured", "your-openai-api-key-here", ""]:
            raise ValueError("OPENAI_API_KEY not configured. Please set OPENAI_API_KEY environment variable.")
        if client is None:
            raise ValueError("OpenAI client not initialized. Please check OPENAI_API_KEY configuration.")
        
        logger.info(f"[AI Stream] Starting stream with model: {model_name}")
        
        stream = await client.chat.completions.create(
            model=model_name,
            messages=conversation,
            stream=True,
            temperature=0.7,
            max_tokens=2000,
        )

        chunk_count = 0
        async for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                
                # Handle content tokens
                if delta.content:
                    content = delta.content
                    chunk_count += 1
                    
                    # Format as SSE - yield immediately for real-time streaming
                    data = json.dumps({"token": content})
                    yield f"data: {data}\n\n"
                
                # Handle finish reason
                if chunk.choices[0].finish_reason:
                    finish_reason = chunk.choices[0].finish_reason
                    logger.info(f"[AI Stream] Finished: {finish_reason} ({chunk_count} chunks)")
                    
                    # Send completion signal
                    if finish_reason == "stop":
                        yield "data: [END_OF_STREAM]\n\n"
                    break

    except RateLimitError as e:
        logger.error(f"[AI Stream] Rate limit error: {e}")
        error_data = json.dumps({
            "error": "Rate limit exceeded. Please try again later.",
            "retryable": True
        })
        yield f"data: {error_data}\n\n"
    
    except APIError as e:
        logger.error(f"[AI Stream] API error: {e}")
        error_data = json.dumps({
            "error": f"OpenAI API error: {str(e)}",
            "retryable": True
        })
        yield f"data: {error_data}\n\n"
    
    except Exception as e:
        logger.exception(f"[AI Stream] Unexpected error: {e}")
        error_data = json.dumps({
            "error": "An unexpected error occurred. Please try again.",
            "retryable": True
        })
        yield f"data: {error_data}\n\n"
    
    finally:
        # Always send end signal
        try:
            yield "data: [END_OF_STREAM]\n\n"
        except Exception:
            pass

async def stream_openai_response_enhanced(
    conversation: List[Dict[str, Any]],
    model_name: str = DEFAULT_MODEL,
    conversation_obj: Optional[Conversation] = None,
    user: Optional[User] = None,
    user_message_content: str = ""
):
    """
    Enhanced async generator to yield OpenAI streaming responses
    with token tracking and persistence.
    """
    start_time = time.time()
    full_response = ""
    tokens_used = 0
    finish_reason = "stop"
    
    try:
        # Check if OpenAI API key is properly configured
        openai_api_key = os.getenv("OPENAI_API_KEY", "")
        if not openai_api_key or openai_api_key in ["sk-placeholder-not-configured", "your-openai-api-key-here", ""]:
            raise ValueError("OPENAI_API_KEY not configured. Please set OPENAI_API_KEY environment variable.")
        if client is None:
            raise ValueError("OpenAI client not initialized. Please check OPENAI_API_KEY configuration.")
        
        logger.info(f"[AI Stream] Starting enhanced stream with model: {model_name}")
        
        stream = await client.chat.completions.create(
            model=model_name,
            messages=conversation,
            stream=True,
            temperature=0.7,
            max_tokens=2000,
        )

        chunk_count = 0
        async for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                
                # Handle content tokens
                if delta.content:
                    content = delta.content
                    full_response += content
                    chunk_count += 1
                    
                    # Format as SSE - yield immediately for real-time streaming
                    data = json.dumps({"token": content})
                    yield f"data: {data}\n\n"
                
                # Handle finish reason
                if chunk.choices[0].finish_reason:
                    finish_reason = chunk.choices[0].finish_reason
                    logger.info(f"[AI Stream] Finished: {finish_reason} ({chunk_count} chunks)")
                    break

        # Calculate tokens used
        tokens_used = await sync_to_async(TokenCounter.count_tokens)(full_response, model_name)
        
        # Save messages to database if conversation exists
        if conversation_obj and user:
            try:
                # Save user message
                user_tokens = await sync_to_async(TokenCounter.count_tokens)(user_message_content, model_name)
                await sync_to_async(ConversationManager.save_message)(
                    conversation_obj,
                    "user",
                    user_message_content,
                    tokens_used=user_tokens,
                    model_used=model_name
                )
                
                # Save assistant message
                await sync_to_async(ConversationManager.save_message)(
                    conversation_obj,
                    "assistant",
                    full_response,
                    tokens_used=tokens_used,
                    model_used=model_name,
                    finish_reason=finish_reason
                )
                
                # Update conversation title if it's the first message
                if conversation_obj.message_count == 2:  # User + Assistant
                    title = await sync_to_async(ConversationManager.generate_title)(user_message_content, conversation_obj.mode)
                    conversation_obj.title = title
                    await sync_to_async(conversation_obj.save)(update_fields=["title"])
                
                # Track analytics
                response_time = time.time() - start_time
                await sync_to_async(AnalyticsTracker.track_request)(
                    user,
                    conversation_obj,
                    tokens_used + user_tokens,
                    conversation_obj.mode,
                    response_time
                )
            except Exception as e:
                logger.error(f"[AI Stream] Error saving to database: {e}")

    except RateLimitError as e:
        logger.error(f"[AI Stream] Rate limit error: {e}")
        error_data = json.dumps({
            "error": "Rate limit exceeded. Please try again later.",
            "retryable": True
        })
        yield f"data: {error_data}\n\n"
    
    except APIError as e:
        logger.error(f"[AI Stream] API error: {e}")
        error_data = json.dumps({
            "error": f"OpenAI API error: {str(e)}",
            "retryable": True
        })
        yield f"data: {error_data}\n\n"
    
    except Exception as e:
        logger.exception(f"[AI Stream] Unexpected error: {e}")
        error_data = json.dumps({
            "error": "An unexpected error occurred. Please try again.",
            "retryable": True
        })
        yield f"data: {error_data}\n\n"
    
    finally:
        # Always send end signal
        try:
            yield "data: [END_OF_STREAM]\n\n"
        except Exception:
            pass

async def get_openai_response_async(
    conversation: List[Dict[str, Any]],
    model_name: str = DEFAULT_MODEL
) -> str:
    """
    Non-streaming async helper to get the full response.
    Used for audio and image processing.
    """
    try:
        # Check if OpenAI API key is properly configured
        openai_api_key = os.getenv("OPENAI_API_KEY", "")
        if not openai_api_key or openai_api_key in ["sk-placeholder-not-configured", "your-openai-api-key-here", ""]:
            raise ValueError("OPENAI_API_KEY not configured. Please set OPENAI_API_KEY environment variable.")
        if client is None:
            raise ValueError("OpenAI client not initialized. Please check OPENAI_API_KEY configuration.")
        
        completion = await client.chat.completions.create(
            model=model_name,
            messages=conversation,
            stream=False,
            temperature=0.7,
            max_tokens=2000,
        )
        logger.info("[AI Async] Response received")
        return completion.choices[0].message.content
    except RateLimitError as e:
        logger.error(f"[AI Async] Rate limit error: {e}")
        raise Exception("Rate limit exceeded. Please try again later.")
    except APIError as e:
        logger.error(f"[AI Async] API error: {e}")
        raise Exception(f"OpenAI API error: {str(e)}")
    except Exception as e:
        logger.exception(f"[AI Async] Unexpected error: {e}")
        raise Exception("An unexpected error occurred. Please try again.")

# ============================================================
# TEXT CHAT ENDPOINT (Async + Streaming)
# ============================================================

@extend_schema(exclude=True)
@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
async def chat_api(request):
    """
    Streaming text chat endpoint.
    Returns Server-Sent Events (SSE) for real-time streaming.
    """
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        from django.http import HttpResponse
        response = HttpResponse()
        response['Access-Control-Allow-Origin'] = request.headers.get('Origin', 'http://localhost:3000')
        response['Access-Control-Allow-Credentials'] = 'true'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response['Access-Control-Max-Age'] = '86400'
        return response
    
    if request.method != 'POST':
        response = JsonResponse(
            {"error": "Method not allowed"},
            status=405
        )
        response['Access-Control-Allow-Origin'] = request.headers.get('Origin', 'http://localhost:3000')
        response['Access-Control-Allow-Credentials'] = 'true'
        return response
    
    try:
        # Parse request body
        body = request.body
        if not body:
            response = JsonResponse(
                {"error": "Request body is required"},
                status=400
            )
            response['Access-Control-Allow-Origin'] = request.headers.get('Origin', 'http://localhost:3000')
            response['Access-Control-Allow-Credentials'] = 'true'
            return response
        
        data = json.loads(body)
        
        # Extract and validate data
        user_data = data.get('user', {})
        mode = data.get('mode', 'Advisor')
        messages = data.get('messages', [])
        conversation_id = data.get('conversation_id')

        # Enhanced validation using InputSanitizer
        sanitized_messages, sanitize_error = await sync_to_async(InputSanitizer.sanitize_messages)(messages)
        if sanitize_error:
            logger.warning(f"[/api/ai/chat] Sanitization failed: {sanitize_error}")
            response = JsonResponse({"error": sanitize_error}, status=400)
            response['Access-Control-Allow-Origin'] = request.headers.get('Origin', 'http://localhost:3000')
            response['Access-Control-Allow-Credentials'] = 'true'
            return response

        # Validate user data
        if not user_data or not user_data.get('id'):
            response = JsonResponse({"error": "User data is required"}, status=400)
            response['Access-Control-Allow-Origin'] = request.headers.get('Origin', 'http://localhost:3000')
            response['Access-Control-Allow-Credentials'] = 'true'
            return response

        # Get user from database
        # User model uses 'userId' field, not 'id'
        user_id = user_data.get('id') or user_data.get('userId')
        try:
            user = await sync_to_async(User.objects.get)(userId=user_id)
        except User.DoesNotExist:
            response = JsonResponse({"error": "User not found"}, status=404)
            response['Access-Control-Allow-Origin'] = request.headers.get('Origin', 'http://localhost:3000')
            response['Access-Control-Allow-Credentials'] = 'true'
            return response

        # Check AI consent
        if not await sync_to_async(has_ai_consent)(user, company=user.company if hasattr(user, 'company') else None):
            response = JsonResponse({
                "error": "AI usage consent is required",
                "error_code": "CONSENT_REQUIRED",
                "consent_type": "ai_usage"
            }, status=403)
            response['Access-Control-Allow-Origin'] = request.headers.get('Origin', 'http://localhost:3000')
            response['Access-Control-Allow-Credentials'] = 'true'
            return response

        # Rate limiting - use userId (primary key) for rate limiting
        user_id_str = str(user.userId)
        rate_ok, rate_error = await sync_to_async(RateLimiter.check_rate_limit)(user_id_str)
        if not rate_ok:
            response = JsonResponse({"error": rate_error}, status=429)
            response['Access-Control-Allow-Origin'] = request.headers.get('Origin', 'http://localhost:3000')
            response['Access-Control-Allow-Credentials'] = 'true'
            return response

        # Increment rate limit
        await sync_to_async(RateLimiter.increment_rate_limit)(user_id_str)

        # Validate mode
        valid_modes = ["Advisor", "Developer", "Researcher", "Learner", "Sales", "Marketing", "Customer Support", "Task Manager"]
        if mode not in valid_modes:
            response = JsonResponse({"error": f"Invalid mode. Must be one of: {', '.join(valid_modes)}"}, status=400)
            response['Access-Control-Allow-Origin'] = request.headers.get('Origin', 'http://localhost:3000')
            response['Access-Control-Allow-Credentials'] = 'true'
            return response

        # Get or create conversation
        conversation_obj = None
        if conversation_id:
            try:
                conversation_obj = await sync_to_async(ConversationManager.get_or_create_conversation)(
                    user,
                    conversation_id,
                    mode
                )
            except Exception as e:
                logger.warning(f"[/api/ai/chat] Error loading conversation: {e}")
                # Continue without conversation persistence if there's an error

        # Get last user message for title generation
        user_message_content = ""
        for msg in reversed(sanitized_messages):
            if msg.get("role") == "user":
                user_message_content = msg.get("content", "")
                break

        logger.info(
            f"[/api/ai/chat] Request from {user.email} | "
            f"Mode: {mode} | Messages: {len(sanitized_messages)} | "
            f"Conversation: {conversation_obj.id if conversation_obj else 'new'}"
        )

        # Build enhanced conversation context
        enhanced_context = await sync_to_async(PromptEnhancer.build_enhanced_context)(
            user_data,
            mode,
            sanitized_messages[:-1] if len(sanitized_messages) > 1 else None
        )
        
        # Combine context with messages
        conversation = enhanced_context + sanitized_messages

        # Enhanced streaming with persistence
        async_gen = stream_openai_response_enhanced(
            conversation,
            model_name=DEFAULT_MODEL,
            conversation_obj=conversation_obj,
            user=user,
            user_message_content=user_message_content
        )
        
        def sync_generator():
            import asyncio
            import queue
            import threading
            
            # Queue to pass chunks from async to sync
            chunk_queue = queue.Queue(maxsize=10)  # Small buffer for smooth streaming
            exception_holder = [None]
            finished = threading.Event()
            
            def run_async_gen():
                """Run async generator in a separate thread with its own event loop"""
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    async def consume():
                        try:
                            async for chunk in async_gen:
                                chunk_queue.put(chunk)
                            chunk_queue.put(None)  # Sentinel to signal completion
                        except Exception as e:
                            exception_holder[0] = e
                            chunk_queue.put(None)
                    new_loop.run_until_complete(consume())
                finally:
                    new_loop.close()
                    finished.set()
            
            # Start async generator in background thread
            thread = threading.Thread(target=run_async_gen, daemon=True)
            thread.start()
            
            # Yield chunks as they arrive (immediate streaming)
            while True:
                try:
                    # Get chunk with small timeout to check for completion
                    chunk = chunk_queue.get(timeout=0.1)
                    if chunk is None:  # Sentinel - generation complete
                        if exception_holder[0]:
                            raise exception_holder[0]
                        break
                    yield chunk
                except queue.Empty:
                    # Check if thread finished
                    if finished.is_set():
                        if exception_holder[0]:
                            raise exception_holder[0]
                        break
                    continue
        
        # Stream response with proper async-to-sync conversion
        response = StreamingHttpResponse(
            sync_generator(),
            content_type='text/event-stream',
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        # Disable buffering for real-time streaming
        response['X-Content-Type-Options'] = 'nosniff'
        # CORS headers for streaming
        response['Access-Control-Allow-Origin'] = request.headers.get('Origin', 'http://localhost:3000')
        response['Access-Control-Allow-Credentials'] = 'true'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        
        return response

    except json.JSONDecodeError:
        logger.error("[/api/ai/chat] Invalid JSON")
        response = JsonResponse({"error": "Invalid JSON"}, status=400)
        response['Access-Control-Allow-Origin'] = request.headers.get('Origin', 'http://localhost:3000')
        response['Access-Control-Allow-Credentials'] = 'true'
        return response
    
    except Exception as e:
        logger.exception(f"[/api/ai/chat] Unexpected error: {e}")
        response = JsonResponse(
            {"error": "An unexpected error occurred"},
            status=500
        )
        response['Access-Control-Allow-Origin'] = request.headers.get('Origin', 'http://localhost:3000')
        response['Access-Control-Allow-Credentials'] = 'true'
        return response

# ============================================================
# AUDIO CHAT ENDPOINT (Sync + Non-Streaming)
# ============================================================

@extend_schema(exclude=True)
@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def audio_chat_api(request):
    """
    Audio chat endpoint with transcription.
    Accepts audio file, transcribes it, and returns AI response.
    """
    try:
        # Validate file
        file = request.FILES.get('file')
        if not file:
            return api_response(
                http_status.HTTP_400_BAD_REQUEST,
                "failure",
                {},
                "MISSING_FILE",
                "No audio file provided"
            )
        
        # Validate file size
        if file.size > MAX_IMAGE_SIZE:
            return api_response(
                http_status.HTTP_400_BAD_REQUEST,
                "failure",
                {},
                "FILE_TOO_LARGE",
                f"File size exceeds {MAX_IMAGE_SIZE / 1024 / 1024}MB"
            )

        # Parse request data
        try:
            user_data = json.loads(request.data.get('user', '{}'))
            mode = request.data.get('mode', 'Advisor')
            messages_data = json.loads(request.data.get('messages', '[]'))
        except json.JSONDecodeError as e:
            logger.error(f"[/api/ai/audio-chat] Invalid JSON: {e}")
            return api_response(
                http_status.HTTP_400_BAD_REQUEST,
                "failure",
                {},
                "INVALID_JSON",
                f"Invalid JSON input: {str(e)}"
            )

        # Validation
        is_valid, error_msg = validate_user_data(user_data)
        if not is_valid:
            return api_response(
                http_status.HTTP_400_BAD_REQUEST,
                "failure",
                {},
                "VALIDATION_ERROR",
                error_msg
            )
        
        is_valid, error_msg = validate_mode(mode)
        if not is_valid:
            return api_response(
                http_status.HTTP_400_BAD_REQUEST,
                "failure",
                {},
                "VALIDATION_ERROR",
                error_msg
            )

        logger.info(
            f"[/api/ai/audio-chat] Audio from {user_data.get('email')} | "
            f"Mode: {mode} | Size: {file.size} bytes"
        )

        temp_in_path = ""
        temp_out_path = ""

        async def async_audio_processing():
            nonlocal temp_in_path, temp_out_path
            
            # Save uploaded file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_in:
                for chunk in file.chunks():
                    temp_in.write(chunk)
                temp_in_path = temp_in.name
            
            temp_out_path = temp_in_path.replace(".webm", ".wav")

            # Convert WebM → WAV using ffmpeg
            process = await asyncio.create_subprocess_exec(
                "ffmpeg", "-i", temp_in_path, "-ar", "16000", "-ac", "1", "-f", "wav", temp_out_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                raise Exception(f"FFmpeg error: {stderr.decode()}")
            
            logger.info(f"[/api/ai/audio-chat] Converted to WAV: {temp_out_path}")

            # Check if OpenAI API key is properly configured
            openai_api_key = os.getenv("OPENAI_API_KEY", "")
            if not openai_api_key or openai_api_key in ["sk-placeholder-not-configured", "your-openai-api-key-here", ""]:
                raise ValueError("OPENAI_API_KEY not configured. Please set OPENAI_API_KEY environment variable.")
            if client is None:
                raise ValueError("OpenAI client not initialized. Please check OPENAI_API_KEY configuration.")

            # Transcribe audio
            with open(temp_out_path, "rb") as audio_file:
                transcription = await client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                )
            
            user_text = transcription.text.strip()
            logger.info(f"[/api/ai/audio-chat] Transcription: {user_text[:50]}...")
            return user_text

        try:
            user_text = async_to_sync(async_audio_processing)()
        except Exception as e:
            logger.exception(f"[/api/ai/audio-chat] Processing error: {e}")
            return api_response(
                http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                "failure",
                {},
                "PROCESSING_ERROR",
                f"Audio processing failed: {str(e)}"
            )
        finally:
            # Cleanup temp files
            for path in [temp_in_path, temp_out_path]:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass

        # Build conversation
        user_context = build_user_context(user_data, mode)
        conversation = (
            [ONE_INTELLIGENT_CONTEXT, user_context] +
            messages_data +
            [{"role": "user", "content": user_text}]
        )

        # Get AI response
        try:
            full_response = async_to_sync(get_openai_response_async)(
                conversation,
                model_name=DEFAULT_MODEL
            )
            
            return api_response(
                http_status.HTTP_200_OK,
                "success",
                {"token": full_response},
            )
        except Exception as e:
            logger.exception(f"[/api/ai/audio-chat] OpenAI error: {e}")
            return api_response(
                http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                "failure",
                {},
                "AI_ERROR",
                str(e)
            )

    except Exception as e:
        logger.exception(f"[/api/ai/audio-chat] Unexpected error: {e}")
        return api_response(
            http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            status="failure",
            data={},
            error_code="SERVER_ERROR",
            error_message="An unexpected error occurred"
        )

# ============================================================
# IMAGE CHAT ENDPOINT (Sync + Non-Streaming)
# ============================================================

@extend_schema(exclude=True)
@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def image_chat_api(request):
    """
    Image analysis endpoint.
    Accepts image file and text, returns AI analysis.
    """
    try:
        # Validate file
        file = request.FILES.get('file')
        if not file:
            return api_response(
                http_status.HTTP_400_BAD_REQUEST,
                "failure",
                {},
                "MISSING_FILE",
                "No image file provided"
            )
        
        # Validate file size
        if file.size > MAX_IMAGE_SIZE:
            return api_response(
                http_status.HTTP_400_BAD_REQUEST,
                "failure",
                {},
                "FILE_TOO_LARGE",
                f"File size exceeds {MAX_IMAGE_SIZE / 1024 / 1024}MB"
            )
        
        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if file.content_type not in allowed_types:
            return api_response(
                http_status.HTTP_400_BAD_REQUEST,
                "failure",
                {},
                "INVALID_FILE_TYPE",
                f"File type must be one of: {', '.join(allowed_types)}"
            )

        # Parse request data
        try:
            user_data = json.loads(request.data.get('user', '{}'))
            mode = request.data.get('mode', 'Advisor')
            messages_data = json.loads(request.data.get('messages', '[]'))
        except json.JSONDecodeError as e:
            logger.error(f"[/api/ai/image-chat] Invalid JSON: {e}")
            return api_response(
                http_status.HTTP_400_BAD_REQUEST,
                "failure",
                {},
                "INVALID_JSON",
                f"Invalid JSON input: {str(e)}"
            )

        # Validation
        is_valid, error_msg = validate_user_data(user_data)
        if not is_valid:
            return api_response(
                http_status.HTTP_400_BAD_REQUEST,
                "failure",
                {},
                "VALIDATION_ERROR",
                error_msg
            )
        
        is_valid, error_msg = validate_mode(mode)
        if not is_valid:
            return api_response(
                http_status.HTTP_400_BAD_REQUEST,
                "failure",
                {},
                "VALIDATION_ERROR",
                error_msg
            )

        logger.info(
            f"[/api/ai/image-chat] Image from {user_data.get('email')} | "
            f"Mode: {mode} | Type: {file.content_type} | Size: {file.size} bytes"
        )

        # Convert image to base64
        image_bytes = file.read()
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        image_url = f"data:{file.content_type};base64,{image_base64}"

        # Get user's text message
        last_user_message = "Please analyze this image and describe it."
        if messages_data:
            for msg in reversed(messages_data):
                if msg.get("role") == "user" and isinstance(msg.get("content"), str):
                    last_user_message = msg.get("content", "").strip()
                    break
        
        # Build conversation with image
        user_context = build_user_context(user_data, mode)
        conversation = [ONE_INTELLIGENT_CONTEXT, user_context]
        
        # Add previous messages (text only)
        for msg in messages_data:
            if isinstance(msg.get("content"), str):
                conversation.append({
                    "role": msg.get("role"),
                    "content": msg.get("content")
                })
        
        # Add image message
        conversation.append({
            "role": "user",
            "content": [
                {"type": "text", "text": last_user_message},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_url,
                        "detail": "high"
                    }
                }
            ]
        })

        # Get AI response
        try:
            full_response = async_to_sync(get_openai_response_async)(
                conversation,
                model_name=DEFAULT_MODEL
            )
            
            return api_response(
                http_status.HTTP_200_OK,
                "success",
                {"token": full_response},
            )
        except Exception as e:
            logger.exception(f"[/api/ai/image-chat] OpenAI error: {e}")
            return api_response(
                http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                "failure",
                {},
                "AI_ERROR",
                str(e)
            )

    except Exception as e:
        logger.exception(f"[/api/ai/image-chat] Unexpected error: {e}")
        return api_response(
            http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            status="failure",
            data={},
            error_code="SERVER_ERROR",
            error_message="An unexpected error occurred"
        )
