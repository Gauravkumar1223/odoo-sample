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
import librosa
import torch
from transformers import AutoProcessor, SeamlessM4TForSpeechToText


aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")
_logger = logging.getLogger(__name__)


class RealTimeService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RealTimeService, cls).__new__(cls)
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
            xmlrpc_port = 8069  # Default value
            _logger.warning(
                f"xmlrpc_port not found in configuration. Falling back to default port: {xmlrpc_port}"
            )

        websocket_port = xmlrpc_port + 1000

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
            # Check for proper audio_chunk_base64 format
            if "," not in audio_chunk_base64:
                _logger.error(f"Improper format for audio_chunk_base64: {audio_chunk_base64[:50]}...")
                models = ["deepgram", "assemblyai", "faster-whisper", "seamless"]
                if audio_chunk_base64 in models:
                    self.transcribe_model = audio_chunk_base64
                    _logger.info(f"Transcribe model set to {self.transcribe_model}")
                continue

            base64_encoded_data = audio_chunk_base64.split(",")[1]
            try:
                audio_chunk = base64.b64decode(base64_encoded_data)
                self._append_to_session_file(session_id, audio_chunk)
                transcription_data = await self.divide_audio(file_path, self.transcribe_model)
                await websocket.send(transcription_data)
            except Exception as e:
                _logger.error(f"Error during decoding and conversion: {e}")

    async def divide_audio(self, audio_file, transcribe_model):
        """Determines the appropriate transcription function based on the model and transcribes the audio."""
        if transcribe_model == "faster-whisper":
            function_handler = self.real_transcribe_chunk_fasterWhisper
        else:
            function_handler = self.real_transcribe_chunk_seamless

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

    def real_transcribe_chunk_seamless(self, chunk_file):
        """Transcribes audio using the Seamless model."""
        audio = AudioSegment.from_file(chunk_file)
        temp_audio_path = self._create_temp_audio_file(audio)

        test_audio = AudioSegment.from_file(temp_audio_path)
        if self._is_audio_short(test_audio):
            os.remove(temp_audio_path)
            return ""

        transcription = ""
        try:
            # Transcribe the segment using seamless model here
            audio_file_path = temp_audio_path
            audio_data, orig_freq = librosa.load(audio_file_path, sr=16000)
            audio_chunk = torch.tensor(audio_data).unsqueeze(0)
            inputs = self.processor(audios=audio_chunk, sampling_rate=16000, return_tensors="pt")
            output_tokens = self.seamless_model.generate(**inputs, tgt_lang="eng")
            transcription = self.processor.decode(output_tokens[0].tolist(), skip_special_tokens=True)
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

    async def _realtime_transcribe_handler(self, websocket, language_param='fr'):
        # Initialize Deepgram with the API key
        api_key = os.getenv("DEEPGRAM_API_KEY")
        if not api_key:
            api_key = "d7172ee47ba2e16a99b48e8d13636f28ad9b835c"
            _logger.error("DEEPGRAM_API_KEY environment not set, using default value.")

        deepgram = Deepgram(api_key)
        _logger.info("Deepgram initialized.")

        # Create a websocket connection to Deepgram for live transcription

        deepgram_options = {
            "smart_format": True,
            "punctuate": True,
            "interim_results": False,
            "encoding": "linear16",
            "language": language_param,
        }
        # Assign the model based on language if needed
        if language_param in ['fr', 'de']:
            deepgram_options["model"] = "enhanced"
        elif language_param in ['en']:
            deepgram_options["model"] = "nova-2"
        else:
            _logger.error(f"Unsupported language parameter: {language_param}")
            return  # Or handle the unsupported language case as needed

        try:
            deepgramLive = await deepgram.transcription.live(deepgram_options)
            _logger.info("Deepgram live transcription initialized.")
        except Exception as e:
            _logger.error("Error connecting to Deepgram: " + str(e))

        # Log when the connection closes
        deepgramLive.registerHandler(
            deepgramLive.event.CLOSE,
            lambda _: _logger.info("Connection to Deepgram closed in event."),
        )
        _logger.info("Deepgram live transcription Close Handler Resgistered.")
        # When transcripts are received from Deepgram, send them to the client's WebSocket
        deepgramLive.registerHandler(
            deepgramLive.event.TRANSCRIPT_RECEIVED,
            lambda transcript: asyncio.create_task(
                self._log_and_send_transcript(websocket, transcript)
            ),
        )
        _logger.info("Deepgram live transcription Close Handler Resgistered.")

        try:
            # Receive audio data from your websocket connection and send it to Deepgram for transcription
            async for audio_chunk_base64 in websocket:
                if "," not in audio_chunk_base64:
                    _logger.error(
                        f"Improper format for audio_chunk_base64: {audio_chunk_base64[:50]}..."
                    )
                    continue

                base64_encoded_data = audio_chunk_base64.split(",")[1]
                try:
                    audio_chunk = base64.b64decode(base64_encoded_data)
                    converted_audio = self._convert_to_wav_pcm16(audio_chunk)

                    deepgramLive.send(converted_audio)

                except Exception as e:
                    _logger.error(f"Error during decoding and conversion: {e}")

        except Exception as e:
            _logger.error(f"Error while streaming audio chunks: {e}")
        finally:
            # Indicate that we've finished sending data and close the connection
            await deepgramLive.finish()

    async def _log_and_send_transcript(self, websocket, transcript):
        # Log the received transcript from Deepgram
        # _logger.info(f"Received transcript from Deepgram: {transcript}")

        try:
            if transcript["type"] == "Results":
                transcribed_text = self._extract_text_from_transcript(transcript)

                # Convert the entire transcript to a JSON string
                transcript_json_string = json.dumps(transcript)

                # Log the message you are about to send to the client
                #    _logger.info(
                #        f"Sending transcribed text to client: {transcript_json_string}"
                #    )

                await websocket.send(transcript_json_string)
            else:
                _logger.info(
                    f"Not sending non-transcription data: {transcript['type']}"
                )
        except Exception as e:
            _logger.error(f"Error sending transcript to client: {e}")

    def _extract_text_from_transcript(self, transcript):
        return (
            transcript.get("channel", {})
            .get("alternatives", [{}])[0]
            .get("transcript", "")
        )

    async def _random_number_handler(self, websocket):
        send_coro = asyncio.create_task(self._send_random_numbers(websocket))
        receive_coro = asyncio.create_task(self._receive_client_numbers(websocket))
        await asyncio.wait(
            [send_coro, receive_coro], return_when=asyncio.FIRST_COMPLETED
        )

    async def _send_random_numbers(self, websocket):
        while not websocket.closed:
            try:
                server_random_number = random.randint(0, 100)
                response_message = f"Server-RNG = {server_random_number} : Client RNG = {self.latest_client_random_number}"
                await websocket.send(response_message)
                await asyncio.sleep(0.02)
            except Exception as e:
                _logger.error(f"An error occurred: {e}")
                break

    async def _receive_client_numbers(self, websocket):
        try:
            async for message in websocket:
                try:
                    _logger.info("Received number from client: %s", message)
                    self.latest_client_random_number = int(message)
                except ValueError:
                    _logger.error(f"Received invalid data: {message}")
        except Exception:
            _logger.info("WebSocket connection closed by the client.")

    async def _realtime_transcribe_handler_assembly(self, websocket):
        transcriber = aai.RealtimeTranscriber(
            sample_rate=16_000,
            on_data=self._on_data,
            on_error=self._on_error,
            on_open=self._on_open,
            on_close=self._on_close,
        )

        transcriber.connect()

        try:
            async for audio_chunk_base64 in websocket:
                if "," not in audio_chunk_base64:
                    _logger.error(
                        f"Improper format for audio_chunk_base64: {audio_chunk_base64[:50]}..."
                    )
                    continue

                base64_encoded_data = audio_chunk_base64.split(",")[1]
                try:
                    audio_chunk = base64.b64decode(base64_encoded_data)
                    converted_audio = self._convert_to_wav_pcm16(audio_chunk)
                    transcriber.stream(converted_audio)
                except Exception as e:
                    _logger.error(f"Error during decoding and conversion: {e}")

        except Exception as e:
            _logger.error(f"Error while streaming audio chunks: {e}")
        finally:
            transcriber.close()

    @staticmethod
    def _convert_to_wav_pcm16(audio_chunk):
        return audio_chunk

    @staticmethod
    def _on_open(session_opened: aai.RealtimeSessionOpened):
        _logger.info(
            f"Transcription session opened with Session ID: {session_opened.session_id}"
        )

    @staticmethod
    def _on_data(transcript: aai.RealtimeTranscript):
        if transcript.text:
            log_msg = (
                f"Final Transcript: {transcript.text}"
                if isinstance(transcript, aai.RealtimeFinalTranscript)
                else f"Partial Transcript: {transcript.text}"
            )
            _logger.info(log_msg)

    @staticmethod
    def _on_error(error: aai.RealtimeError):
        _logger.error(f"Error occurred during transcription: {error}")

    @staticmethod
    def _on_close():
        _logger.info("Transcription session closed.")

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

    async def _close_websocket_server_and_event_loop(self):
        if self.websocket_server:
            self.websocket_server.close()
            await self.websocket_server.wait_closed()

        # Add sentinel task to ensure the _process_tasks loop exits
        self.task_queue.put_nowait(None)

        # Cancel all the tasks
        tasks = asyncio.all_tasks(self.event_loop)
        for task in tasks:
            task.cancel()

        await asyncio.gather(*tasks, return_exceptions=True)

        if self.websocket_thread:
            self.websocket_thread.join()
            self.server_started = False

        _logger.info("Service stopped.")

    async def async_cleanup_function(self):
        if self.websocket_server:
            self.websocket_server.close()
            await self.websocket_server.wait_closed()

        # Cancel all the tasks
        for task in self.tasks:
            task.cancel()

        await asyncio.gather(*self.tasks, return_exceptions=True)

    # Instantiate the service when the module is imported.
    # real_time_service_instance = RealTimeService()

    async def transcribe_from_websocket_speech(self, websocket):
        # Prepare the speech recognizer
        push_stream = speechsdk.audio.PushAudioInputStream()
        audio_config = speechsdk.audio.AudioConfig(stream=push_stream)

        self.speech_recognizer = speechsdk.SpeechRecognizer(
            speech_config=self.speech_config, audio_config=audio_config
        )

        # Connect callbacks to the events fired by the speech recognizer
        self.speech_recognizer.recognizing.connect(
            lambda e: asyncio.create_task(
                self.send_text_to_client(websocket, e.result.text, is_final=False)
            )
        )
        self.speech_recognizer.recognized.connect(
            lambda e: asyncio.create_task(
                self.send_text_to_client(websocket, e.result.text, is_final=True)
            )
        )

        # Start continuous speech recognition
        self.speech_recognizer.start_continuous_recognition()

        try:
            # Receive audio data from the WebSocket connection and send it to Azure for transcription
            async for message in websocket:
                if isinstance(message, bytes):
                    audio_chunk = message
                    push_stream.write(audio_chunk)
                elif isinstance(message, str) and message == "stop":
                    push_stream.close()
                    break
        except Exception as e:
            print(f"Error while streaming audio chunks: {e}")
        finally:
            # Stop continuous recognition
            self.speech_recognizer.stop_continuous_recognition()

    async def send_text_to_client(self, websocket, text, is_final):
        try:
            transcript = {"text": text, "is_final": is_final}
            transcript_json_string = json.dumps(transcript)
            await websocket.send(transcript_json_string)
        except Exception as e:
            print(f"Error sending transcript to client: {e}")
