import os
import json
import base64
import tempfile
import subprocess
import logging
import asyncio
from django.http import StreamingHttpResponse
from rest_framework.decorators import api_view
from openai import OpenAI
from dotenv import load_dotenv

# ===============================
# 🌍 Environment Setup
# ===============================
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

logger = logging.getLogger("oneintelligent.ai")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

ONE_INTELLIGENT_CONTEXT = {
    "role": "system",
    "content": """
You are **Oneintelligent AI**, the AI companion of the One Intelligence workspace ecosystem.
Use the structured response framework and tone for answers.
"""
}

# ===============================
# 💬 Helper: Stream OpenAI Response
# ===============================
async def stream_openai_response(conversation):
    try:
        with client.responses.stream(
            model="gpt-5",
            input=conversation
        ) as stream:
            for event in stream:
                if event.type == "response.output_text.delta":
                    yield event.delta.encode("utf-8")
                elif event.type == "response.completed":
                    break
                await asyncio.sleep(0.001)
    except Exception as e:
        logger.error(f"[AI Stream] ❌ Error: {e}")
        yield f"\n[Error] {str(e)}".encode("utf-8")


# ===============================
# 💬 TEXT CHAT STREAMING ENDPOINT
# ===============================
@api_view(['POST'])
def chat_api(request):
    body = request.data
    user_data = body.get('user', {})
    mode = body.get('mode', '')
    messages = body.get('messages', [])

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

    async def generator():
        async for chunk in stream_openai_response(conversation):
            yield chunk

    return StreamingHttpResponse(generator(), content_type='text/plain')


# ===============================
# 🎙️ AUDIO CHAT STREAMING ENDPOINT
# ===============================
@api_view(['POST'])
def audio_chat_api(request):
    try:
        file = request.FILES['file']
        user_data = json.loads(request.data.get('user', '{}'))
        mode = request.data.get('mode', '')
        messages_data = json.loads(request.data.get('messages', '[]'))

        logger.info(f"[/api/ai/audio-chat] Received audio from {user_data.get('email')} | Mode: {mode}")

        # Convert WebM → WAV
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_in:
            temp_in.write(file.read())
            temp_in.flush()
            temp_in_path = temp_in.name

        temp_out_path = temp_in_path.replace(".webm", ".wav")
        subprocess.run(
            ["ffmpeg", "-i", temp_in_path, "-ar", "16000", "-ac", "1", "-f", "wav", temp_out_path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Transcribe
        with open(temp_out_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=audio_file,
            )
        user_text = transcription.text.strip()
        logger.info(f"🗣️ Transcription: {user_text}")

        user_context = {
            "role": "system",
            "content": f"""
User Info:
- Name: {user_data.get('name')}
- Email: {user_data.get('email')}
- Mode: {mode}
"""
        }

        conversation = [ONE_INTELLIGENT_CONTEXT, user_context] + messages_data + [{"role": "user", "content": user_text}]

        async def generator():
            async for chunk in stream_openai_response(conversation):
                yield chunk

        return StreamingHttpResponse(generator(), content_type='text/plain')

    except Exception as e:
        logger.error(f"[/api/ai/audio-chat] ❌ Error: {e}")
        return Response({"error": str(e)}, status=400)


# ===============================
# 🖼️ IMAGE CHAT STREAMING ENDPOINT
# ===============================
@api_view(['POST'])
def image_chat_api(request):
    try:
        file = request.FILES['file']
        user_data = json.loads(request.data.get('user', '{}'))
        mode = request.data.get('mode', '')
        messages_data = json.loads(request.data.get('messages', '[]'))

        logger.info(f"[/api/ai/image-chat] Received image from {user_data.get('email')} | Mode: {mode}")

        # Convert image to base64
        image_bytes = file.read()
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        image_url = f"data:{file.content_type};base64,{image_base64}"

        last_user_message = ""
        if messages_data:
            for msg in reversed(messages_data):
                if msg.get("role") == "user":
                    last_user_message = msg.get("content", "").strip()
                    break
        if not last_user_message:
            last_user_message = "Please analyze this image and describe it."

        system_context = {
            "role": "system",
            "content": [
                {
                    "type": "input_text",
                    "text": (
                        "You are a coding and design assistant. Analyze image layout, produce semantic HTML/CSS."
                    ),
                }
            ],
        }

        user_context = {
            "role": "user",
            "content": [
                {"type": "input_text", "text": last_user_message},
                {"type": "input_image", "image_url": image_url},
            ],
        }

        conversation = [system_context, user_context]

        async def generator():
            async for chunk in stream_openai_response(conversation):
                yield chunk

        return StreamingHttpResponse(generator(), content_type='text/plain')

    except Exception as e:
        logger.error(f"[/api/ai/image-chat] ❌ Error: {e}")
        return Response({"error": str(e)}, status=400)
