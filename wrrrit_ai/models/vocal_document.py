# -*- coding: utf-8 -*-
import asyncio
import base64
import io
import json
import logging
import mimetypes
import os
import tempfile
import time
import warnings
from datetime import datetime

import assemblyai as aai
import openai
from azure.cognitiveservices.speech import ResultReason, CancellationReason
from azure.cognitiveservices.speech import SpeechConfig, SpeechRecognizer, AudioConfig
from langchain.chains import VectorDBQA
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from pydub import AudioSegment

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from . import prompts
from .azure_llm import AzureLLM
from .back_ground_handler import run_background_action
# from wrrrit_collector.models.wrrrit_collector_data import WrrritDataLakeEntry
from .voice_record_ai_actions import VoiceRecordAiActions
from .wrrrit_knowledge import persist_directory

warnings.simplefilter("ignore")

_logger = logging.getLogger(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")


class AiVoiceRecord(models.Model):
    _name = "wrrrit.ai.voice_record"
    _description = "Voice Record"

    # Method to download file
    @api.model
    def download_file(self):
        """Overridden to use custom file name"""
        pass

    # Method to get default locale
    @api.model
    def _get_default_locale(self):
        # Get the user's language (e.g., "en_US")
        user_lang = self.env.user.lang

        # Extract the language part (e.g., "en")
        lang_part = user_lang.split("_")[0] if user_lang else ""

        # Map to your field values
        lang_map = {
            "en": "english",
            "de": "german",
            "fr": "french",
            "it": "italian",
            "es": "spanish",
            "pt": "portuguese",
            "nl": "dutch",
            "tr": "turkish",
            "ar": "arabic",
        }

        return lang_map.get(lang_part, "english")  # Default to 'english' if no match

    # Method to get default report template
    @api.model
    def _default_report_template(self):
        return self.env["wrrrit.ai.report"].search([], limit=1)

    name = fields.Char("Voice Record Name", required=True, default="Voice Record")
    voice_file = fields.Binary("Voice File", default=b"", attachment=False)
    voice_file_name = fields.Char(
        "Voice File Name", required=True, default="VoiceFile.mp3"
    )
    generated_file = fields.Binary("Generated PDF Report", attachment=False)
    generated_file_name = fields.Char(string="Generated PDF Filename")

    generated_docx_name = fields.Char(string="Generated DOCX Filename")

    generated_docx = fields.Binary("Generated Word Document", attachment=False)
    docx_url = fields.Char(string="Open With Office")
    pdf_reports = fields.One2many(
        "wrrrit.ai.voice_record.pdf", "voice_record_id", string="Generated PDF Reports"
    )

    transcription_data = fields.Text("Transcript")
    corrected_transcription_data = fields.Text("Corrected Transcript")
    transcription_stream = fields.Text(string="Transcription Stream")
    translated_data = fields.Text("Translated Transcript")
    generated_summary = fields.Text("Summary")
    generated_report = fields.Text("Generated Report")
    document_id = fields.Many2one("wrrrit.ai.document", string="Records")
    creation_date = fields.Date("Creation Date", default=fields.Date.context_today)
    extracted_metadata = fields.Text("Extracted Data", default="{}")
    wrrrit_llm = AzureLLM(stream=False)

    @api.model
    def download_file(self):
        """Overridden to use custom file name"""
        pass

    @api.model
    def _get_default_locale(self):
        # Get the user's language (e.g., "en_US")
        user_lang = self.env.user.lang

        # Extract the language part (e.g., "en")
        lang_part = user_lang.split("_")[0] if user_lang else ""

        # Map to your field values
        lang_map = {
            "fr": "french",
            "en": "english",
            "de": "german",
            "it": "italian",
            "es": "spanish",
            "pt": "portuguese",
            "nl": "dutch",
            "tr": "turkish",
            "ar": "arabic",
        }

        return lang_map.get(lang_part, "english")  # Default to 'english' if no match

    record_locale = fields.Selection(
        [
            ("french", "Générer du Français"),
            ("english", "Generate English"),
            ("german", "Generate German"),
            ("italian", "Generare Italiano"),
            ("spanish", "Generar Español"),
            ("portuguese", "Gerar Português"),
            ("dutch", "Genereren in het Nederlands"),
            ("turkish", "Yazılımı Türkçe Yaz"),
            ("arabic", "توليد اللغة العربية"),
        ],
        string="Report Language",
        default=_get_default_locale,
    )

    @api.model
    def _default_report_template(self):
        return self.env["wrrrit.ai.report"].search([], limit=1)

    report_template = fields.Many2one(
        "wrrrit.ai.report", string="Report Template", default=_default_report_template
    )
    custom_ai_sections = fields.Text("Custom AI Sections")
    latest_transcription_timestamp = fields.Datetime("Latest Transcription Timestamp")
    latest_report_timestamp = fields.Datetime("Latest Report Timestamp")

    last_updated = fields.Datetime(
        "Last Updated", compute="_compute_last_updated", store=True, readonly=True
    )

    drugs_diseases = fields.Text("Drugs and Diseases")
    corrected_drugs_diseases = fields.Text("Corrected Drugs and Diseases")
    is_user_admin = fields.Boolean(search="_search_is_user_admin")

    def _search_is_user_admin(self, operator, value):
        if operator not in ["=", "!="] or not isinstance(value, bool):
            raise UserError(_("Invalid search operator or value for is_user_admin"))
        is_true = (operator == "=" and value) or (operator != "=" and not value)
        user_is_admin = self.env.user.has_group("base.group_system")
        if (is_true and user_is_admin) or (not is_true and not user_is_admin):
            return []  # Return an empty domain to match all records
        else:
            return [("id", "=", 0)]  # Return a domain to match no records

    owner_id = fields.Many2one(
        comodel_name="res.users",
        string="Owner",
        default=lambda self: self.env.user,
        help="The user who owns this record.",
    )

    @api.depends(
        "name",
        "voice_file",
        "generated_file",
        "transcription_data",
        "translated_data",
        "generated_summary",
        "generated_report",
        "creation_date",
        "record_locale",
        "document_id",
        "custom_ai_sections",
    )
    def _compute_last_updated(self):
        for record in self:
            record.last_updated = fields.Datetime.now()

    @api.model
    def create(self, vals):
        record = super(AiVoiceRecord, self).create(vals)
        current_date = datetime.now().strftime("%y%m%d")
        record.write({"name": "Record-{}-{}".format(current_date, record.id)})
        record.write(
            {"voice_file_name": "Record-{}-{}.mp3".format(current_date, record.id)}
        )

        return record

    def action_generate_report(self):
        if not self.transcription_data:
            self.action_voice_record_transcribe()
        try:
            voice_ai = VoiceRecordAiActions()
            voice_ai.action_generate_report(self)

        except Exception as e:
            # Log the error
            _logger.error("Error generating report: %s", str(e))
            # Raise a UserError to notify the user
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Error"),
                    "message": _("Error Generating Report: %s") % str(e),
                    "sticky": True,  # True means the notification will not disappear until the user closes it
                    "type": "danger",  # This will show the notification with a red background
                },
            }

    def action_transcription_translate(self):
        doc_ai = VoiceRecordAiActions()
        doc_ai.action_translate_transcript(self)

    def action_drugs_diseases(self):
        doc_ai = VoiceRecordAiActions()
        doc_ai.action_drugs_diseases(self)

    def action_corrected_drugs_diseases(self):
        for record in self:
            embedding = OpenAIEmbeddings()
            vectordb = Chroma(
                persist_directory=persist_directory, embedding_function=embedding
            )
            qa = VectorDBQA.from_chain_type(
                llm=self.wrrrit_llm.llm,
                chain_type="stuff",
                vectorstore=vectordb,
            )

            query = (
                    "Correct the names of drugs and diseases: "
                    + (record.drugs_diseases or "N/A")
                    + "\n"
                    + "in this locale : "
                    + (record.record_locale or "N/A")
            )

            response = qa.run(query)
            record.corrected_drugs_diseases = response

    def action_correct_transcription(self):
        for record in self:
            embedding = OpenAIEmbeddings()
            vectordb = Chroma(
                persist_directory=persist_directory, embedding_function=embedding
            )
            qa = VectorDBQA.from_chain_type(
                llm=self.wrrrit_llm.llm,
                chain_type="stuff",
                vectorstore=vectordb,
            )

            query = (
                    "Correct the names of drugs and diseases in this transcription: "
                    + (record.transcription_data or "N/A")
                    + "\n"
                    + (record.corrected_drugs_diseases or "N/A")
                    + "in this locale : "
                    + (record.record_locale or "english")
            )
            vectordb2 = Chroma(
                persist_directory=persist_directory, embedding_function=embedding
            )

            response = qa.run(query)
            record.corrected_drugs_diseases = response

    def action_voice_record_transcribe(self):
        try:
            AiVoiceRecord.action_voice_record_transcribe_assemblyai(self)

        except Exception as e:
            # Log the error
            _logger.error("Error transcribing voice record: %s", str(e))
            # Raise a UserError to notify the user
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Error"),
                    "message": _("Error Transcription, Save Record and Try Again"),
                    "sticky": False,  # True means the notification will not disappear until the user closes it
                    "type": "danger",  # This will show the notification with a red background
                },
            }

    def action_voice_record_transcribe_assemblyai(self):
        aai.settings.api_key = f"ad10f16a95c642f4862714432176ab02"
        config = aai.TranscriptionConfig(
            language_detection=True,
            speaker_labels=True,
            punctuate=True,
            format_text=True,
        )

        transcriber = aai.Transcriber(config=config)

        document = self

        if not document.exists():
            _logger.error("Document with ID: %s does not exist", self.id)
            return {"error": "Document not found."}

        audio_data = base64.b64decode(self.voice_file)

        if not audio_data:
            _logger.error("No audio data found in field")
            return {"error": "No audio data found."}

        # Create a temporary file to save the audio data
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=True) as temp_file:
            temp_file.write(audio_data)
            temp_file.flush()  # Ensure data is written to disk

            mime_type = mimetypes.guess_type(temp_file.name)[0]

            transcript = transcriber.transcribe(temp_file.name)
            transcription_result = ""

            utterances = transcript.utterances

            # For each utterance, print its speaker and what was said
            for utterance in utterances:
                speaker = utterance.speaker
                text = utterance.text
                transcription_result = (
                        transcription_result + "\n" + f"Speaker {speaker}: {text}"
                )

            # Update the specified transcription field with the result
            self.transcription_data = transcription_result

    def action_voice_record_transcribe_deepgram(self):
        from deepgram import Deepgram

        dg_client = Deepgram("7c8e25b12e7735c51fa94bd5a9da92a861e908d4")

        document = self

        if not document.exists():
            _logger.error("Document with ID: %s does not exist", self.id)
            return {"error": "Document not found."}

        audio_data = base64.b64decode(self.voice_file)

        if not audio_data:
            _logger.error("No audio data found in field")
            return {"error": "No audio data found."}

        # Create a temporary file to save the audio data
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=True) as temp_file:
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

                transcription_result = transcript
                # ...
                transcription_text = ""

                if "results" in transcription_result:
                    for channel in transcription_result["results"]["channels"]:
                        for alternative in channel["alternatives"]:
                            previous_speaker = None
                            for word_info in alternative["words"]:
                                speaker = f"Speaker {word_info['speaker']}"
                                if speaker != previous_speaker:
                                    transcription_text += f"\n{speaker}: "
                                    previous_speaker = speaker
                                transcription_text += f"{word_info['word']} "

                self.transcription_data = transcription_text

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

    def action_voice_record_transcribe_azure(self):
        _logger.info(
            "Transcribing with Azure Speech Service for document ID: %s", self.id
        )

        # Azure Speech Service API key and region
        speech_key = os.getenv("SPEECH_KEY", "YourAzureSubscriptionKey")
        service_region = os.getenv("SPEECH_REGION", "YourServiceRegion")

        document = self

        if not document.exists():
            _logger.error("Document with ID: %s does not exist", self.id)
            return {"error": "Document not found."}

        audio_data = base64.b64decode(document.voice_file)

        if not audio_data:
            _logger.error("No audio data found in field")
            return {"error": "No audio data found."}

        # Convert MP3 audio data to WAV format
        audio_stream = io.BytesIO(
            audio_data
        )  # Use BytesIO object as a buffer for the audio data
        audio_stream.seek(0)  # Go to the start of the stream
        mp3_audio = AudioSegment.from_file(audio_stream, format="mp3")
        wav_stream = io.BytesIO()
        mp3_audio.export(wav_stream, format="wav")
        wav_data = wav_stream.getvalue()

        # Create a temporary file to save the converted WAV audio data
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_file.write(wav_data)
            temp_file_name = temp_file.name

        # Transcribe the WAV audio using Azure Speech Service
        try:
            speech_config = SpeechConfig(subscription=speech_key, region=service_region)
            audio_config = AudioConfig(filename=temp_file_name)

            speech_recognizer = SpeechRecognizer(
                speech_config=speech_config, audio_config=audio_config
            )

            _logger.info("Starting transcription with Azure Speech Service")
            result = speech_recognizer.recognize_once()

            if result.reason == ResultReason.RecognizedSpeech:
                _logger.info("Recognized: {}".format(result.text))
                transcription_result = result.text
            elif result.reason == ResultReason.NoMatch:
                _logger.error("No speech could be recognized")
                transcription_result = ""
            elif result.reason == ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                _logger.error(
                    "Speech Recognition canceled: {}".format(
                        cancellation_details.reason
                    )
                )
                if cancellation_details.reason == CancellationReason.Error:
                    _logger.error(
                        "Error details: {}".format(cancellation_details.error_details)
                    )
                transcription_result = ""
        except Exception as e:
            _logger.error("Error transcribing voice record: {}".format(str(e)))
            transcription_result = ""
        finally:
            # Always delete the temporary file
            os.remove(temp_file_name)

        # Update the specified transcription field with the result
        document.transcription_data = transcription_result or "N/A"
        return {"success": True, "transcription": transcription_result}

    def custom_button_2(self):
        pass

    # threading.Thread(target=self.fetch_chat_stream, args=(self.id,)).start()

    @api.model
    def fetch_chat_stream(self, record_id):
        # Create a new environment for this thread
        with api.Environment.manage():
            new_env = api.Environment(
                self.pool.cursor(), self.env.uid, self.env.context
            )
            record = new_env["wrrrit.ai.voice_record"].browse(record_id)

            response_obj = openai.ChatCompletion.create(
                model="gpt-3.5-turbo-16k",
                messages=[
                    {
                        "role": "user",
                        "content": "write a 20000 words poem about tunisia",
                    }
                ],
                max_tokens=2000,
                temperature=0,
                stream=True,
            )

            answer = ""
            for event in response_obj:
                event_text = event["choices"][0]["delta"]
                answer += event_text.get("content", "")
                record.transcription_data = answer
                # Commit the transaction to see the changes immediately in the UI
                new_env.cr.commit()
            # Don't forget to close the cursor when done
            new_env.cr.close()

    def custom_button_3(self):
        pass

    def extract_metadata(self):
        for record in self:
            system = prompts.system_dictionary()
            user = prompts.extract_metadata(record.transcription_data)
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ]

            response = self.wrrrit_llm.call_llm(messages, max_tokens=8000)

            try:
                # Strip the leading and trailing triple single quotes
                first_bracket_position = response.find("{")
                last_bracket_position = response.rfind("}")

                if first_bracket_position != -1 and last_bracket_position != -1:
                    cleaned_string = response[
                                     first_bracket_position: last_bracket_position + 1
                                     ]
                else:
                    cleaned_string = ""  # or however you want to handle no match

                # Parse the cleaned string to a dictionary
                data = json.loads(cleaned_string)

                record.extracted_metadata = self.generate_meta_report(data)
                name = data.get("First Name", "")
                last_name = data.get("Last Name", "")
                dob_str = data.get("Date of Birth", "")
                metadata = data

                try:
                    dob = (
                        datetime.strptime(dob_str, "%Y-%m-%d")
                        if dob_str
                        else datetime.strptime("1990-01-01", "%Y-%m-%d")
                    )
                except ValueError:
                    dob = datetime.strptime(
                        "1990-01-01", "%Y-%m-%d"
                    )  # Set default date if dob_str is incorrect

                # Create a new data lake entrys
                self.env["wrrrit.data_lake.entry"].create_data_lake_entry(
                    name, last_name, dob, data
                )

            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON string, JSONDecodeError: {e}")
            except ValueError as e:
                raise ValueError(f"ValueError occurred: {e}")
            except Exception as e:
                raise ValueError(f"An unexpected error occurred: {e}")

    @staticmethod
    def get_first_json_object(json_string):
        import json

        decoder = json.JSONDecoder()
        pos = 0
        json_object = None
        try:
            json_object, pos = decoder.raw_decode(json_string)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON string: {e}")

        return json_object

    @staticmethod
    def generate_meta_report(json_data):
        try:
            report_text = ""
            for key, value in json_data.items():
                if isinstance(value, dict):
                    sub_report = f"{key}:\n"
                    for sub_key, sub_value in value.items():
                        sub_report += f"  - {sub_key}: {sub_value}\n"
                    report_text += f"{sub_report}\n"
                else:
                    report_text += f"{key}: {value}\n"
            return report_text
        except Exception as e:
            return f"An error occurred while generating the report: {str(e)}"

    @run_background_action
    def action_process_A(self):
        return "Process A Completed"

    def action_process_B(self):
        # Your long-running process B code goes here
        _logger.info("Process B started in Action definition")

        _logger.info("Process B Finished in Action definition")
        return "Process B Completed in Action Definition"

    task_status = fields.Char(string="Task Status", default="pending")
    task_id = fields.Char(string="Task ID")

    def start_long_task(self, task_id):
        # Logic to start the long-running task
        self.task_id = task_id

        self.task_status = "in_progress"
        time.sleep(10)
        self.task_status = "completed"
        return self.task_status
