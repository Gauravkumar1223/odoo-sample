# -*- coding: utf-8 -*-
from dotenv import load_dotenv
from odoo import api, fields, models
import base64
import os, time
import json
from pydub import AudioSegment
import threading
import asyncio
import mimetypes
import tempfile

from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
    Microphone,
    FileSource,
    PrerecordedOptions,
)
load_dotenv()

class FileQuestion(models.Model):
    _name = 'file.question'
    _description = 'File & Question'


    file_data = fields.Binary(string='Select an audio file', attachment=True, help="Select the file to upload")
    question = fields.Text(string='Partial Transcription')
    answer = fields.Text(string="Final Transcription")

    locale = fields.Selection(
        [("en", "English"), ("fr", "French"), ("es", "Spanish"), ("de", "German"), ("it", "Italian"),
         ("pt", "Portuguese"), ("ru", "Russian"), ("zh", "Chinese"), ("ar", "Arabic"), ("ja", "Japanese")],
        string="Language")

    transcripted_text = fields.Text(string="Transcripted Text")



    def process_chunk(self, chunk_file, index):
    # API key for Deepgram service
        API_KEY = "7c8e25b12e7735c51fa94bd5a9da92a861e908d4"
        # Initialize Deepgram client
        deepgram = DeepgramClient(API_KEY)

        # Read chunk file as binary data
        with open(chunk_file, "rb") as file:
            buffer_data = file.read()

        # Prepare payload for transcribing the chunk
        payload: FileSource = {
            "buffer": buffer_data,
        }

        # Define transcribing options
        options = PrerecordedOptions(
            model="nova-2",
            smart_format=True,
        )

        # Transcribe the chunk using Deepgram API
        response = deepgram.listen.prerecorded.v("1").transcribe_file(payload, options)
        # Convert transcription response to JSON format
        transcription = response.to_json(indent=4)
        # Extract transcription data from JSON
        data = json.loads(transcription)["results"]["channels"][0]["alternatives"][0]["transcript"]

        # Store metadata information for the chunk
        metadata_entry = {
            "index": index,
            "data": data
        }
        metadata.append(metadata_entry)

        # Remove the processed chunk file
        os.remove(chunk_file)
        print("--------------------------------------------------", data)
        return data


        # Method to convert the uploaded audio file and process its chunks
    def convert_audio_file(self):
        # Decode the binary audio data
        global metadata
        metadata = []
        decoded_data = base64.b64decode(self.file_data)
        # Write the decoded audio data to a WAV file
        with open('audio.wav', 'wb') as audio:
            audio.write(decoded_data)

        # Define chunk length in milliseconds
        chunk_length_ms = 30 * 1000
        # Load the audio file and convert it to a PyDub audio segment
        audio = AudioSegment.from_file("audio.wav")

        threads = []

        # Iterate through the audio file in chunks
        for i in range(0, len(audio), chunk_length_ms):
            # Extract the chunk
            chunk = audio[i:i + chunk_length_ms]
            # Export the chunk to a temporary WAV file
            chunk_file = f"chunk_{i}.wav"
            chunk.export(chunk_file, format="wav")

            # Create a thread to process the chunk
            thread = threading.Thread(target=self.process_chunk, args=(chunk_file, i,))
            thread.start()
            threads.append(thread)

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        final_str = ""
        # The transcription chunks order gets mixed up, so we need to sort them by index ( temporary solution )
        sorted_list = sorted(metadata, key=lambda x: x['index'])

        # Concatenate transcriptions from sorted chunks
        for data in sorted_list:
            final_str += data['data'] + " "

        # Store the final transcription
        self.answer = final_str


    # vocal file code also blocking the UI I have tried it.
    def async_convert_audio_file(self):
        from deepgram import Deepgram
        dg_client = Deepgram("7c8e25b12e7735c51fa94bd5a9da92a861e908d4")

        audio_data = base64.b64decode(self.file_data)

        # Create a temporary file to save the audio data
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_file.flush()  # Ensure data is written to disk
            # Get the mime type of the file
            mime_type = mimetypes.guess_type(temp_file.name)[0]
            # Transcribe the audio using the OpenAI Whisper API
            with open(temp_file.name, "rb") as audio:
                source = {"buffer": audio, "mimetype": "audio/mp3"}
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    transcript = loop.run_until_complete(
                        self.async_transcribe(dg_client, source)
                    )
                finally:
                    loop.close()

                print(transcript)
                self.answer = transcript['results']['channels'][0]['alternatives'][0]['transcript']


    async def async_transcribe(self, dg_client, source):
        transcript = await dg_client.transcription.prerecorded(
                source,
                {
                    "punctuate": True,
                    "utterances": False,
                    "model": "enhanced",
                    "detect_language": True,
                    "detect_entities": False,
                    "smart_format": True,
                    "diarize": True,
                    "numerals": True,
                },
            )

        return transcript

    def convert_audio_file(self):
        print("Hello World")

    def async_convert_audio_file(self):
        print("Hello World")

