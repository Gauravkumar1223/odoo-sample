# Audio Transcription Service

This project provides a service for real-time transcription of audio data received over a WebSocket connection. It utilizes different transcription models to handle various types of audio inputs and supports multiple languages.


## Git
- frynol_reports_generic_vishal




## Features

- Handles incoming audio data over WebSocket.
- Decodes audio data, transcribes it using specified models, and sends back the transcription.
- Supports multiple transcription models, such as Faster Whisper and Seamless.
- Dynamically selects the appropriate transcription function based on the chosen model.
- Utilizes asynchronous programming with asyncio for efficient handling of audio streams.
- Provides error handling and logging for better debugging.

## Usage

1. Start the WebSocket server.
2. Send audio data in Base64 format to the server.
3. Receive transcribed text over WebSocket.

## How It Works

- The `checking` method listens for incoming audio data over WebSocket.
- It decodes the Base64 encoded audio chunks, appends them to session files, and then transcribes them using the appropriate model.
- The `divide_audio` method selects the transcription function based on the chosen model and runs it asynchronously using `asyncio`.
- Transcription functions (`real_transcribe_chunk_fasterWhisper` and `real_transcribe_chunk_seamless`) transcribe audio data using specific models (Faster Whisper and Seamless).
- Temporary audio files are created for processing and removed afterward.
- Error handling is implemented to catch and log any exceptions during decoding and transcription.

## Project Structure

- `audio_sessions/`: Directory to store audio session files.
- `wrrrit_realtime_service.py`: Contains the main WebSocket server and audio transcription logic.
- `README.md`: Documentation file.
- `requirements.txt`: Dependency list.

## Dependencies

- Python 3.7+
- `asyncio`: Asynchronous programming library.
- `websockets`: WebSocket library.
- `pydub`: Audio manipulation library.
- `torch`: Deep learning framework (for Seamless model).
- `librosa`: Audio processing library (for Seamless model).
- `transformers`: Library for natural language understanding (for Seamless model).
- `whisper-faster`
- `seamless`

## Setup

1. Install dependencies: `pip install -r requirements.txt`.
2. Run locally for checking




