import asyncio
import atexit
import base64
import json
import logging
import random
import threading
from urllib.parse import urlparse, parse_qs
import concurrent.futures
import assemblyai as aai
import azure.cognitiveservices.speech as speechsdk
import websockets
from deepgram import Deepgram
import uuid
import odoo
from faster_whisper import WhisperModel
from pydub import AudioSegment
import os
from transformers import AutoProcessor, SeamlessM4TForSpeechToText



_logger = logging.getLogger(__name__)


class RealtimeWhisher:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RealtimeWhisher, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        atexit.register(self.stop_service)

        # add termination event
        self.terminate_event = threading.Event()

        self.websocket_thread = None
        self.websocket_server = None
        self.event_loop = asyncio.new_event_loop()

        asyncio.set_event_loop(self.event_loop)
        self.tasks = []

        self.task_queue = asyncio.Queue()
        self.latest_client_random_number = 0
        self.server_started = False
        self.shutdown_flag = False

        self.start_service()
        self.speech_key = os.getenv("SPEECH_KEY")
        self.service_region = os.getenv("SPEECH_REGION")
        self.speech_config = None
        self.speech_recognizer = None
        self.model_size = "base"
        self.segment = 0
        self.device = "cpu"
        self.compute_type = "float32"
        self.model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
        self.segment = 3072
        self.start_time = 0
        self.end_time = self.segment
        self.processor = AutoProcessor.from_pretrained("facebook/hf-seamless-m4t-medium")
        self.seamless_model = SeamlessM4TForSpeechToText.from_pretrained("facebook/hf-seamless-m4t-medium")
        self.transcribe_model = "deepgram"

        if not self.speech_key or not self.service_region:
            _logger.error(
                "Environment variables for SPEECH_KEY and SPEECH_REGION must be set."
            )
        else:
            self.speech_config = speechsdk.SpeechConfig(
                subscription=self.speech_key, region=self.service_region
            )
            self.speech_config.speech_recognition_language = (
                "en-US"  # Set the language according to your preference.
            )

    def __del__(self):
        self.stop_service()

    def start_service(self):
        if not self.websocket_thread:
            self.websocket_thread = threading.Thread(
                target=self._run_websocket_server, daemon=True
            )
            self.websocket_thread.start()
            self.server_started = True

    def _run_websocket_server(self):
        asyncio.set_event_loop(self.event_loop)

        try:
            xmlrpc_port = int(odoo.tools.config.get("http_port"))
            _logger.info(
                f"Successfully retrieved XML-RPC port from configuration: {xmlrpc_port}"
            )
        except KeyError:
            xmlrpc_port = 8080  # Default value
            _logger.warning(
                f"xmlrpc_port not found in configuration. Falling back to default port: {xmlrpc_port}"
            )

        websocket_port = 8080

        self.websocket_server = websockets.serve(
            self.websocket_handler, "0.0.0.0", websocket_port
        )
        self.event_loop.run_until_complete(self.websocket_server)
        _logger.info(f"WebSocket server started on port {websocket_port}.")

        # Handle queued tasks
        self.event_loop.run_until_complete(self._process_tasks())

    async def _process_tasks(self):
        while not self.shutdown_flag:
            task = await self.task_queue.get()
            if task is None:  # Sentinel to terminate the loop
                break
            await task

    async def websocket_handler(self, websocket, path):
        query_string = urlparse(websocket.path).query
        _logger.info(f"Received connection from client with path: {path}")
        language_param = parse_qs(query_string).get('language', ['en'])[0]  # Default to 'en' if not set
        _logger.info(f"Received connection from client with language: {language_param}")

        await self.checking(websocket, language_param)



    async def checking(self, websocket, language_param):
        """Handles incoming audio data over websocket, decodes, transcribes, and sends back transcription."""
        session_id = str(uuid.uuid4())
        file_path = self._initialize_session_file(session_id)

        async for audio_chunk_base64 in websocket:

            print("audio_chunk_base64:--", audio_chunk_base64[:50],"---------------------------------")
            # base64_encoded_data = audio_chunk_base64.split(",")[1]
            try:
                audio_chunk = audio_chunk_base64

                if audio_chunk == "close":
                    print(audio_chunk)
                    # empty the queue and the directory
                    self.task_queue.put_nowait(None)
                    #remove all the files in the directory
                    for file in os.listdir("audio_sessions"):
                        os.remove(f"audio_sessions/{file}")

                    break
                self._append_to_session_file(session_id, audio_chunk)
                transcription_data = await self.divide_audio(file_path)
                await websocket.send(transcription_data)
            except Exception as e:
                _logger.error(f"Error during decoding and conversion: {e}")



    async def divide_audio(self, audio_file):
        """Determines the appropriate transcription function based on the model and transcribes the audio."""
        function_handler = self.real_transcribe_chunk_fasterWhisper

        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            transcription = await loop.run_in_executor(pool, function_handler, audio_file)
            _logger.info(f"Transcription: {transcription}")
        return transcription



    def real_transcribe_chunk_fasterWhisper(self, chunk_file):
        """Transcribes audio using the Faster Whisper model."""
        audio = AudioSegment.from_file(chunk_file)
        temp_audio_path = self._create_temp_audio_file(audio)

        test_audio = AudioSegment.from_file(temp_audio_path)
        if self._is_audio_short(test_audio):
            os.remove(temp_audio_path)
            return ""

        transcription = ""
        try:
            segments, info = self.model.transcribe(temp_audio_path, beam_size=5)
            transcription = " ".join([segment.text for segment in segments])
            _logger.info(f"Detected language: {info.language} with probability {info.language_probability}")
            _logger.info(f"Transcription: {transcription}")
        except Exception as e:
            _logger.error(f"Error during transcription: {e}")
        finally:
            _logger.info("Removing temporary audio file")
            os.remove(temp_audio_path)
            self._update_audio_segment_times()
        return transcription



    def _initialize_session_file(self, session_id):
        """Initializes and returns the file path for the audio session."""
        dir_path = "audio_sessions"
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        file_path = f"{dir_path}/{session_id}.wav"
        open(file_path, 'wb').close()
        return file_path



    def _append_to_session_file(self, session_id, audio_chunk):
        """Appends an audio chunk to the session file."""
        file_path = f"audio_sessions/{session_id}.wav"
        with open(file_path, 'ab') as file:
            file.write(audio_chunk)



    def _create_temp_audio_file(self, audio):
        """Creates a temporary audio file and returns its path."""
        temp_audio_path = f"audio_sessions/temp_audio_{random.randint(0, 10000)}.wav"
        audio[self.start_time:self.end_time].export(temp_audio_path, format="wav")
        return temp_audio_path



    def _is_audio_short(self, test_audio):
        """Checks if the audio segment is shorter than expected and logs accordingly."""
        if len(test_audio) < self.segment:
            _logger.info("Audio segment is shorter than expected, skipping transcription.")
            return True
        return False



    def _update_audio_segment_times(self):
        """Updates the start and end times for audio processing."""
        self.start_time += self.segment
        self.end_time += self.segment

    def stop_service(self):
        _logger.info("Stopping service...")

        # If the event loop is running, shut it down safely
        if self.event_loop.is_running():
            # Add the shutdown task to the event loop
            asyncio.run_coroutine_threadsafe(
                self._close_websocket_server_and_event_loop(), self.event_loop
            )
        else:
            # If not, run the cleanup directly
            self.event_loop.run_until_complete(
                self._close_websocket_server_and_event_loop()
            )

        # Close the event loop if it's not closed already
        if not self.event_loop.is_closed():
            self.event_loop.close()

        _logger.info("Service stopped.")