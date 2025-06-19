import asyncio
import json
import logging
import os
import random
import string
import time

import assemblyai as aai
import websockets
from werkzeug.wrappers import Response

from odoo import http

aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")

_logger = logging.getLogger(__name__)


class RealtimeController(http.Controller):
    config = aai.TranscriptionConfig(language_detection=True, speaker_labels=True)

    # set the configuration
    transcriber = aai.Transcriber(config=config)

    @http.route("/ai_wrrrit/realtime/stream", type="http", auth="user", methods=["GET"])
    def stream_text(self):
        def generate():
            while True:
                # Generate a random character
                random_char = random.choice(string.ascii_letters)
                _logger.info(f"Generated character: {random_char}")
                yield f"data: {random_char}\n\n"
                # Wait for 500 milliseconds before the next iteration
                time.sleep(0.05)

        headers = {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
        return Response(generate(), headers=headers)

        # Define a new route to handle audio chunks

    @http.route(
        "/voice_recorder/stream_audio", type="http", auth="user", methods=["POST"]
    )
    def stream_audio(self, audio_chunk, **kwargs):
        # Send the audio chunk to AssemblyAI for transcription
        transcription = self.transcribe_audio(audio_chunk)
        # Return the transcription to the frontend
        return http.request.make_response(json.dumps({"transcription": transcription}))

    # Helper method to transcribe audio
    def transcribe_audio(self, audio_chunk):
        # Stream the audio chunk to AssemblyAI for transcription

        response = self.transcriber.transcribe(audio_chunk)

        # Extract and return the transcription text
        return response.text

    @http.route(
        "/websocket/voice_recorder/transcription_socket", type="http", auth="user"
    )
    async def transcription_socket(self, request):
        ws = websockets.WebSocketCommonProtocol()
        _logger.info("websocket handshake")

        await ws.handshake(
            request.httprequest.environ["HTTP_UPGRADE"],
            request.httprequest.environ["HTTP_CONNECTION"],
            request.httprequest.environ["HTTP_SEC_WEBSOCKET_KEY"],
            request.httprequest.environ["HTTP_SEC_WEBSOCKET_PROTOCOL"],
            request.httprequest.environ["HTTP_SEC_WEBSOCKET_VERSION"],
        )

        words = [
            "hello",
            "world",
            "this",
            "is",
            "a",
            "test",
            "of",
            "the",
            "transcription",
            "service",
        ]

        while True:
            # Await a message from the client
            message = await ws.recv()
            if message == "close":
                await ws.close()
                break

            # Generate random word and send it to the client
            random_word = random.choice(words)
            await ws.send(random_word)
            await asyncio.sleep(0.3)  # simulate a delay in transcription

        return {}
