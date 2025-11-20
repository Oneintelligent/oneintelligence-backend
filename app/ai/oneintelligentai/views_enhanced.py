"""
Enhanced OneIntelligent AI Backend API
World-class, bulletproof input/output system with persistence, analytics, and security
"""

import os
import json
import asyncio
import logging
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

from app.utils.response import api_response
from rest_framework import status as http_status
from django.contrib.auth import get_user_model

from .services import (
    InputSanitizer,
    RateLimiter,
    TokenCounter,
    ConversationManager,
    AnalyticsTracker,
    PromptEnhancer
)
from .models import Conversation, Message

User = get_user_model()
load_dotenv()

# ============================================================
# CONFIGURATION
# ============================================================

logger = logging.getLogger("oneintelligent.ai")

# OpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Model configuration
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MAX_MESSAGE_LENGTH = 10000
MAX_MESSAGES_PER_REQUEST = 100
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB

# ============================================================
# SYSTEM CONTEXT (Enhanced)
# ============================================================

ONE_INTELLIGENT_CONTEXT = {
  "role": "system",
  "content": """
You are **Oneintelligent AI**, the intelligent companion inside the One Intelligence workspace — built to help every user *Think Smarter, Act Faster, and Grow Continuously*.

Your purpose aligns with the vision and mission of One Intelligence:  
**Empower individuals and businesses to work smarter with unified, simple, AI-powered technology** :contentReference[oaicite:2]{index=2}.

---------------------------------------
### 🌍 Core Identity
- Be simple, intuitive, and helpful — *zero complexity*.  
- Reflect One Intelligence's core principles:  
  **Simplicity, AI-First Intelligence, Unified Experience, Value-Driven Action, Inclusiveness, Continuous Improvement, and Trust** :contentReference[oaicite:3]{index=3}.
- Always guide users toward clarity, progress, and smart decision-making.

---------------------------------------
### 🎯 When Depth or Reasoning Is Needed — Use This Structure
Use ONLY when the task requires analysis, planning, problem-solving, or multi-step reasoning:

1. **Situation** — 2–3 line summary of the user's intent.  
2. **Tasks** — List the steps needed to solve the request.  
3. **Action** — Provide the solution with clarity and relevance.  
4. **Result** — Show the outcome; verify the user’s original ask is addressed.  
5. **Recommendations** — Offer optional improvements or next steps.

---------------------------------------
### 💬 Tone & Behavior
- If the user greets, give a normal, natural response — no framework.  
- Be concise, contextual, and practical.  
- Adapt tone to the user's role (founder, developer, sales, marketing, support, etc.).  
- Encourage better thinking, faster action, and continuous growth.  
- Extract useful insights or next steps when relevant.  
- Offer follow-up questions that deepen clarity or momentum.

---------------------------------------
### 📝 Format Rules (GitHub-Flavored Markdown Only)
**Strict rules — never break these:**

#### Numbered Lists  
- Always keep number + title + text on the **same line**.  
- Example: `1. **Define Milestones** - Outline key delivery checkpoints.`  
- Never place the number on its own line.

#### Headings  
- Always use: `### Heading`  
- Never use plain-text labels like \"Heading:\"  
- Never repeat headings in the same answer.

#### Bullets  
- Use `-` or `*` for unordered lists.

#### Code Blocks  
- Always specify a language: ```python / ```bash etc.  
- Do not add copy buttons or metadata.

#### Spacing  
- Exactly **one blank line** between sections — no more.

---------------------------------------
### 🧠 Product Awareness & Context
You understand One Intelligence’s ecosystem:  
- Unified modules: Projects, Tasks, CRM, Accounts, Support, Campaigns, Dashboard, Admin, Licensing, Teams, FLAC, Conversations :contentReference[oaicite:4]{index=4}  
- Plans: **Pro** (no AI), **Pro Max** (AI Recommendations), **Ultra** (Conversational AI – future) :contentReference[oaicite:5]{index=5}  
- AI role today: Smart recommendations, insights, predictions (not full conversational execution).  
- Conversational ChatOps launch is **Phase 2 (Ultra)**.

When answering, consider the user's plan-level capabilities when relevant.

---------------------------------------
### 🚀 North Star
Every interaction should help the user:  
**Think smarter. Act faster. Grow continuously.**
"""
}


# ============================================================
# ENHANCED STREAMING WITH PERSISTENCE
# ============================================================

async def stream_openai_response_enhanced(
    conversation: List[Dict[str, Any]],
    model_name: str = DEFAULT_MODEL,
    conversation_obj: Optional[Conversation] = None,
    user: Optional[User] = None,
    user_message_content: str = ""
) -> tuple[str, int, str]:
    """
    Enhanced async generator to yield OpenAI streaming responses
    with token tracking and persistence.
    Returns: (full_response, tokens_used, finish_reason)
    """
    start_time = time.time()
    full_response = ""
    tokens_used = 0
    finish_reason = "stop"
    
    try:
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
        tokens_used = TokenCounter.count_tokens(full_response, model_name)
        
        # Save messages to database
        if conversation_obj and user:
            try:
                # Save user message
                user_tokens = TokenCounter.count_tokens(user_message_content, model_name)
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
                    title = ConversationManager.generate_title(user_message_content, conversation_obj.mode)
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

# ============================================================
# ENHANCED TEXT CHAT ENDPOINT
# ============================================================

@extend_schema(exclude=True)
@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
async def chat_api_enhanced(request):
    """
    Enhanced streaming text chat endpoint with:
    - Input sanitization and validation
    - Rate limiting
    - Conversation persistence
    - Token tracking
    - Analytics
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
        response = JsonResponse({"error": "Method not allowed"}, status=405)
        response['Access-Control-Allow-Origin'] = request.headers.get('Origin', 'http://localhost:3000')
        response['Access-Control-Allow-Credentials'] = 'true'
        return response
    
    try:
        # Parse request body
        body = request.body
        if not body:
            response = JsonResponse({"error": "Request body is required"}, status=400)
            response['Access-Control-Allow-Origin'] = request.headers.get('Origin', 'http://localhost:3000')
            response['Access-Control-Allow-Credentials'] = 'true'
            return response
        
        data = json.loads(body)
        
        # Extract data
        user_data = data.get('user', {})
        mode = data.get('mode', 'Advisor')
        messages = data.get('messages', [])
        conversation_id = data.get('conversation_id')
        
        # Validate user data
        if not user_data or not user_data.get('id'):
            response = JsonResponse({"error": "User data is required"}, status=400)
            response['Access-Control-Allow-Origin'] = request.headers.get('Origin', 'http://localhost:3000')
            response['Access-Control-Allow-Credentials'] = 'true'
            return response
        
        # Get user from database
        try:
            user = await sync_to_async(User.objects.get)(id=user_data.get('id'))
        except User.DoesNotExist:
            response = JsonResponse({"error": "User not found"}, status=404)
            response['Access-Control-Allow-Origin'] = request.headers.get('Origin', 'http://localhost:3000')
            response['Access-Control-Allow-Credentials'] = 'true'
            return response
        
        # Rate limiting
        rate_ok, rate_error = await sync_to_async(RateLimiter.check_rate_limit)(str(user.id))
        if not rate_ok:
            response = JsonResponse({"error": rate_error}, status=429)
            response['Access-Control-Allow-Origin'] = request.headers.get('Origin', 'http://localhost:3000')
            response['Access-Control-Allow-Credentials'] = 'true'
            return response
        
        # Increment rate limit
        await sync_to_async(RateLimiter.increment_rate_limit)(str(user.id))
        
        # Validate mode
        valid_modes = ["Advisor", "Developer", "Researcher", "Learner", "Sales", "Marketing", "Customer Support", "Task Manager"]
        if mode not in valid_modes:
            response = JsonResponse({"error": f"Invalid mode. Must be one of: {', '.join(valid_modes)}"}, status=400)
            response['Access-Control-Allow-Origin'] = request.headers.get('Origin', 'http://localhost:3000')
            response['Access-Control-Allow-Credentials'] = 'true'
            return response
        
        # Sanitize and validate messages
        sanitized_messages, sanitize_error = await sync_to_async(InputSanitizer.sanitize_messages)(messages)
        if sanitize_error:
            response = JsonResponse({"error": sanitize_error}, status=400)
            response['Access-Control-Allow-Origin'] = request.headers.get('Origin', 'http://localhost:3000')
            response['Access-Control-Allow-Credentials'] = 'true'
            return response
        
        # Get or create conversation
        conversation_obj = await sync_to_async(ConversationManager.get_or_create_conversation)(
            user,
            conversation_id,
            mode
        )
        
        # Get last user message for title generation
        user_message_content = ""
        for msg in reversed(sanitized_messages):
            if msg.get("role") == "user":
                user_message_content = msg.get("content", "")
                break
        
        # Build enhanced conversation context
        enhanced_context = await sync_to_async(PromptEnhancer.build_enhanced_context)(
            user_data,
            mode,
            sanitized_messages[:-1] if len(sanitized_messages) > 1 else None
        )
        
        # Combine context with messages
        conversation = enhanced_context + sanitized_messages
        
        logger.info(
            f"[/api/ai/chat] Request from {user.email} | "
            f"Mode: {mode} | Messages: {len(sanitized_messages)} | "
            f"Conversation: {conversation_obj.id}"
        )

        # Convert async generator to sync generator for StreamingHttpResponse
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
            
            chunk_queue = queue.Queue(maxsize=10)
            exception_holder = [None]
            finished = threading.Event()
            
            def run_async_gen():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    async def consume():
                        try:
                            async for chunk in async_gen:
                                chunk_queue.put(chunk)
                            chunk_queue.put(None)
                        except Exception as e:
                            exception_holder[0] = e
                            chunk_queue.put(None)
                    new_loop.run_until_complete(consume())
                finally:
                    new_loop.close()
                    finished.set()
            
            thread = threading.Thread(target=run_async_gen, daemon=True)
            thread.start()
            
            while True:
                try:
                    chunk = chunk_queue.get(timeout=0.1)
                    if chunk is None:
                        if exception_holder[0]:
                            raise exception_holder[0]
                        break
                    yield chunk
                except queue.Empty:
                    if finished.is_set():
                        if exception_holder[0]:
                            raise exception_holder[0]
                        break
                    continue
        
        # Stream response
        response = StreamingHttpResponse(
            sync_generator(),
            content_type='text/event-stream',
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        response['X-Content-Type-Options'] = 'nosniff'
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
        response = JsonResponse({"error": "An unexpected error occurred"}, status=500)
        response['Access-Control-Allow-Origin'] = request.headers.get('Origin', 'http://localhost:3000')
        response['Access-Control-Allow-Credentials'] = 'true'
        return response

