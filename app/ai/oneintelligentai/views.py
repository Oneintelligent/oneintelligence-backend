import os
import json
import asyncio
import logging
import base64
import tempfile
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from openai import AsyncOpenAI
from dotenv import load_dotenv
from asgiref.sync import async_to_sync
from drf_spectacular.utils import extend_schema

load_dotenv()

# Use AsyncOpenAI for async views
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

logger = logging.getLogger("oneintelligent.ai")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

ONE_INTELLIGENT_CONTEXT = {
    "role": "system",
    "content": """
You are **Oneintelligent AI**, the AI companion of the One Intelligence workspace ecosystem (Project management, Task management, sales management, customer account management, customer support ticket managment, internal chat all powered with oneintelligent ai to boost productibity by identifying the growth opportunities, risk, remind on pending items, etc— designed to help users *Think, Act, and Grow Smarter & Faster.*

### 🎯 Response Framework
Use the following structure **only when the user’s question or task requires depth or reasoning**:
1. **Situtation** — summarize the intent / situation in 3 lines.  
2. **Taks** — Provide a clear, structured, list of taks
3. **Action** — Describe how to accomplish the tasks. Keep teh content with quality  
4. **Result** — Share the outcome, ensure the original ask is met, else be open to call out the situation.
5. **Recommendations** - Based on industry standards and best practices, recommend options to grow further.

### 💬 Tone & Behavior
- If the user greets (e.g., “hi”, “hello”, “thanks”), respond naturally and conversationally — no structured sections.  
- Be insightful, concise, and context-aware.  
- Tailor your tone to the user’s role (developer, business, creative, etc.).  
- Always encourage better thinking, efficient action, and continuous growth.

Stay aligned with your mission: **Think, Act, and Grow Faster & Smarter.**
"""
}

# ===============================
# Re-usable Async SSE Generator (FOR ASYNC VIEWS ONLY)
# ===============================
async def stream_openai_response_sse(conversation, model_name="gpt-4o-mini"):
    """
    Async generator to yield OpenAI streaming responses
    formatted as Server-Sent Events (SSE).
    """
    try:
        # Use the standard .chat.completions.create method
        stream = await client.chat.completions.create(
            model=model_name,
            messages=conversation,
            stream=True
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                # Get the text chunk
                content = chunk.choices[0].delta.content
                
                # Format as SSE
                data = json.dumps({"token": content})
                yield f"data: {data}\n\n"
            
            if chunk.choices and chunk.choices[0].finish_reason:
                logger.info(f"[AI Stream] Finished with reason: {chunk.choices[0].finish_reason}")
                break

    except Exception as e:
        logger.error(f"[AI Stream] ❌ Error: {e}")
        error_data = json.dumps({"error": str(e)})
        yield f"data: {error_data}\n\n"
    
    finally:
        # Send a special "end" event
        logger.info("[AI Stream] Sending end-of-stream signal.")
        yield "data: [END_OF_STREAM]\n\n"

# ===============================
# Helper for Sync Views to call Async OpenAI (No Streaming)
# ===============================
async def get_openai_response_async(conversation, model_name="gpt-4o-mini"):
    """
    A non-streaming async helper to get the full response.
    """
    try:
        completion = await client.chat.completions.create(
            model=model_name,
            messages=conversation,
            stream=False # No streaming
        )
        logger.info(f"[AI Async Helper] ✅ Got response.")
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"[AI Async Helper] ❌ Error: {e}")
        return f"[Error] {str(e)}"

# ===============================
# 💬 TEXT CHAT ENDPOINT (Full Async + Streaming)
# ===============================
@extend_schema(exclude=True)
@csrf_exempt # Use plain Django decorator for a full async view
async def chat_api(request): # Must be async def
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        # CRITICAL FIX: request.body is already a bytes object, DO NOT await it.
        body = request.body
        data = json.loads(body)
        
        user_data = data.get('user', {})
        mode = data.get('mode', '')
        messages = data.get('messages', [])

        logger.info(f"[/api/ai/chat] From: {user_data.get('email')} | Mode: {mode}")

        user_context = {
            "role": "system",
            "content": f"""
User Info:
- ID: {user_data.get('id')}
- Name: {user_data.get('name')}
- Email: {user_data.get('email')}
Current Mode: {mode}
"""
        }

        conversation = [ONE_INTELLIGENT_CONTEXT, user_context] + messages

        # Use the SSE generator
        generator = stream_openai_response_sse(conversation, model_name="gpt-4o-mini")
        return StreamingHttpResponse(generator, content_type='text/event-stream')

    except json.JSONDecodeError:
        logger.error(f"[/api/ai/chat] ❌ Invalid JSON")
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"[/api/ai/chat] ❌ Error: {e}")
        return JsonResponse({"error": str(e)}, status=400)

# ===============================
# 🎙️ AUDIO CHAT ENDPOINT (Sync View + Non-Streaming Response)
# ===============================
@extend_schema(exclude=True)
@csrf_exempt
@api_view(['POST']) # We can use @api_view here because the view is sync
def audio_chat_api(request): # Must be def (synchronous)
    try:
        # Accessing request.FILES and request.data requires a sync view
        file = request.FILES.get('file')
        if not file:
            return Response({"error": "No file provided"}, status=400)

        user_data = json.loads(request.data.get('user', '{}'))
        mode = request.data.get('mode', '')
        messages_data = json.loads(request.data.get('messages', '[]'))

    except json.JSONDecodeError as e:
        logger.error(f"[/api/ai/audio-chat] Invalid JSON input: {e}")
        return Response({"error": f"Invalid JSON input: {e}"}, status=400)
    except Exception as e:
        logger.error(f"[/api/ai/audio-chat] Error processing form data: {e}")
        return Response({"error": str(e)}, status=400)

    logger.info(f"🎧 Received audio from {user_data.get('email')} | Mode: {mode}")

    temp_in_path = ""
    temp_out_path = ""

    # This helper function will hold all our async logic
    async def async_audio_processing():
        nonlocal temp_in_path, temp_out_path
        # 1️⃣ Convert WebM → WAV using ffmpeg (async)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_in:
            for chunk in file.chunks():
                temp_in.write(chunk)
            temp_in_path = temp_in.name
        
        temp_out_path = temp_in_path.replace(".webm", ".wav")

        process = await asyncio.create_subprocess_exec(
            "ffmpeg", "-i", temp_in_path, "-ar", "16000", "-ac", "1", "-f", "wav", temp_out_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise Exception(f"FFmpeg error: {stderr.decode()}")
        
        logger.info(f"🎵 Converted to WAV: {temp_out_path}")

        # 2️⃣ Transcribe the converted WAV
        with open(temp_out_path, "rb") as audio_file:
            transcription = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
            )
        user_text = transcription.text.strip()
        logger.info(f"🗣️ Transcription: {user_text}")
        return user_text

    try:
        # Use async_to_sync to run our async helper
        user_text = async_to_sync(async_audio_processing)()
    except Exception as e:
        logger.error(f"[/api/ai/audio-chat] ❌ Audio processing error: {e}")
        return Response({"error": f"Audio processing failed: {e}"}, status=500)
    finally:
        # 3️⃣ Cleanup temp files
        if os.path.exists(temp_in_path): os.remove(temp_in_path)
        if os.path.exists(temp_out_path): os.remove(temp_out_path)

    # 4️⃣ Build conversation
    user_context = {"role": "system", "content": f"User Info:\n- Name: {user_data.get('name')}\n- Email: {user_data.get('email')}\n- Mode: {mode}\n"}
    conversation = [ONE_INTELLIGENT_CONTEXT, user_context] + messages_data + [{"role": "user", "content": user_text}]

    # 5️⃣ Get full response (no streaming) using async_to_sync
    full_response = async_to_sync(get_openai_response_async)(conversation, model_name="gpt-4o-mini")
    
    # Return a single JSON response, not a stream
    return Response({"token": full_response})


# ===============================
# 🖼️ IMAGE CHAT ENDPOINT (Sync View + Non-Streaming Response)
# ===============================
@extend_schema(exclude=True)
@csrf_exempt
@api_view(['POST']) # We can use @api_view here because the view is sync
def image_chat_api(request): # Must be def (synchronous)
    try:
        # Accessing request.FILES and request.data requires a sync view
        file = request.FILES.get('file')
        if not file:
            return Response({"error": "No file provided"}, status=400)

        user_data = json.loads(request.data.get('user', '{}'))
        mode = request.data.get('mode', '')
        messages_data = json.loads(request.data.get('messages', '[]'))

    except json.JSONDecodeError as e:
        logger.error(f"[/api/ai/image-chat] Invalid JSON input: {e}")
        return Response({"error": f"Invalid JSON input: {e}"}, status=400)
    except Exception as e:
        logger.error(f"[/api/ai/image-chat] Error processing form data: {e}")
        return Response({"error": str(e)}, status=400)

    # 1️⃣ Convert image to base64 (Sync)
    image_bytes = file.read()
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    image_url = f"data:{file.content_type};base64,{image_base64}"
    logger.info(f"🖼️ Received image from {user_data.get('email')} | Mode: {mode}")

    # 2️⃣ Get user's last text message (Sync)
    last_user_message = "Please analyze this image and describe it."
    if messages_data:
        for msg in reversed(messages_data):
            if msg.get("role") == "user" and isinstance(msg.get("content"), str):
                last_user_message = msg.get("content", "").strip()
                break
    
    # 3️⃣ Build conversation (Sync)
    system_prompt = "You are a coding and design assistant. When given an image, analyze its layout and produce clean, semantic, responsive HTML and inline CSS (or Tailwind if asked). Avoid JavaScript unless explicitly requested."
    conversation = [{"role": "system", "content": system_prompt}]
    for msg in messages_data:
        if isinstance(msg.get("content"), str):
            conversation.append({"role": msg.get("role"), "content": msg.get("content")})
    conversation.append({
        "role": "user",
        "content": [
            {"type": "text", "text": last_user_message},
            {"type": "image_url", "image_url": {"url": image_url, "detail": "high"}}
        ]
    })

    # 4️⃣ Get full response (no streaming) using async_to_sync
    full_response = async_to_sync(get_openai_response_async)(conversation, model_name="gpt-4o-mini")

    # Return a single JSON response
    return Response({"token": full_response})