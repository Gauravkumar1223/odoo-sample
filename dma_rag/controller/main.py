from odoo import http
from odoo.http import request
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
    Microphone,
    FileSource,
    PrerecordedOptions,
)
import json, os
import tempfile
import random
import subprocess

class frynolRag(http.Controller):
    @http.route('/frynol_rag/check/',website=True, auth='public')
    def check(self, **kw):
        # return "Just checking..."
        records = request.env['file.question'].sudo().search([])
        print(records,"---------------------------------------------------------------")
        # return request.render('frynol_rag.patients_page', {
        #     'records': records,
        # })
        return records

    @http.route('/frynol_rag/recording/', website=True, auth='public', methods=['POST'], csrf=False)
    def recording(self, **kw):
        try:
            audio_file = kw.get('audio_file')
            language = kw.get('language')

            if language == "undefined":
                language = "en-US"

            #read the data from mp3 file
            audio_data = audio_file.read()
            # Create a temporary file to hold the audio data
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
                temp_file.write(audio_data)

                # Run ffmpeg to convert the audio data to an MP3 file
                output_mp3_file = temp_file.name

                subprocess.run(['ffmpeg', '-y', '-i', temp_file.name, output_mp3_file])

                print(output_mp3_file)

                deepgram = DeepgramClient('a3e20a666c7fa4a32377d0678e365cf8453c2d3f')
                with open(output_mp3_file, "rb") as file:
                    buffer_data = file.read()

                payload: FileSource = {
                    "buffer": buffer_data,
                }

                options = PrerecordedOptions(
                    model="nova-2",
                    smart_format=True,
                    punctuate=True,
                    detect_language=True,
                    language=language,
                )

                # STEP 3: Call the transcribe_file method with the text payload and options
                response = deepgram.listen.prerecorded.v("1").transcribe_file(payload, options)

                # STEP 4: Print the response
                transcription = response.to_json(indent=4)
                data = json.loads(transcription)["results"]["channels"][0]["alternatives"][0]["transcript"]

                dict = {
                    "data": data,
                    "status": "success",
                }
                return json.dumps(dict)
        except Exception as e:
            dict = {
                "data": str(e),
                "status": "error",
            }

            return json.dumps(dict)




