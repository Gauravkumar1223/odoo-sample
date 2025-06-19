# controllers/main.py
import datetime
import os
import time

from odoo import http
from odoo.http import request
import logging
import openai, base64
import tempfile
import mimetypes
import assemblyai as aai

import warnings

from odoo.addons.wrrrit_ai.models.documents_ai_actions import DocumentAiActions
from odoo.addons.wrrrit_ai.models.voice_record_ai_actions import VoiceRecordAiActions


# Suppress the DeprecationWarning
warnings.filterwarnings("ignore")
_logger = logging.getLogger(__name__)


class frynolAiDocumentController(http.Controller):
    @http.route("/document/chat", type="http", auth="user")
    def chat(self, document_id, user_question, **kwargs):
        document = request.env["wrrrit.ai.document"].browse(int(document_id))

        if document.conversation_chain:
            response = document.conversation_chain({"question": user_question})
            chat_history = response["chat_history"]

            return request.render(
                "wrrrit_ai_document.chat",
                {
                    "chat_history": chat_history,
                },
            )
        else:
            return "No Conversation available. Please upload a document."

    @http.route("/voice_recorder/save_recording", type="json", auth="user")
    def save_recording(self, **kwargs):
        _logger.info("Saving Record to Database ")
        blob = kwargs.get("blob")
        if blob:
            blob_size_kb = len(blob.encode("utf-8")) / 1024
            content = blob[:15]
        else:
            blob_size_kb = 0
            content = "None"

        _logger.info("Size: %.2f KB, Saved : %s", blob_size_kb, content)

        document_id = kwargs.get("id")
        document = request.env["wrrrit.ai.document"].browse(document_id)

        # Check if the document exists
        if document.exists():
            # Update the voice_record field
            document.write({"voice_record": blob})
            _logger.info("Record saved successfully for document ID: %s", document_id)
        else:
            _logger.error(
                "Failed to save record. Document with ID: %s does not exist",
                document_id,
            )

    @http.route("/voice_recorder/delete_recording", type="json", auth="user")
    def delete_recording(self, **kwargs):
        _logger.info("Deleting Record from database ")
        document_id = kwargs.get("id")
        document = request.env["wrrrit.ai.document"].browse(document_id)

        # Check if the document exists
        if document.exists():
            # Remove the voice_record field value
            document.write({"voice_record": False})
            _logger.info("Record deleted successfully for document ID: %s", document_id)
        else:
            _logger.error(
                "Failed to delete record. Document with ID: %s does not exist",
                document_id,
            )

    @http.route("/voice_recorder/load_recording", type="json", auth="user")
    def load_recording(self, **kwargs):
        _logger.info("Loading Record from database ")
        document_id = kwargs.get("id")
        document = request.env["wrrrit.ai.document"].browse(document_id)

        # Check if the document exists
        if document.exists():
            # Retrieve the voice_record field
            voice_record = document.read(["voice_record"])[0]["voice_record"]

            if voice_record:
                _logger.info(
                    "Record loaded successfully for document ID: %s", document_id
                )
                return voice_record
            else:
                _logger.error("No record found for document ID: %s", document_id)
                return None
        else:
            _logger.error(
                "Failed to load record. Document with ID: %s does not exist",
                document_id,
            )




    @http.route("/wrrrit_get_docx/<int:id>", type="http", auth="public", website=True)
    def get_docx(self, id, **kw):
        _logger.debug("Entering get_docx method with id: %s", id)
        import urllib.parse

        record = request.env["wrrrit.ai.voice_record"].sudo().browse(id)
        _logger.debug("Fetched record: %s", record)
        if not record.generated_docx:
            _logger.debug("No generated docx found for record: %s", record)
            return request.not_found()
        filecontent = base64.b64decode(record.generated_docx)
        filename = record.generated_docx_name or "document.docx"
        headers = [
            (
                "Content-Type",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
            (
                "Content-Disposition",
                f"inline; filename*=UTF-8''{urllib.parse.quote(filename)}",
            ),
            ("Content-Length", str(len(filecontent))),
        ]

        _logger.info("Filename: %s", filename)
        _logger.debug("Exiting get_docx method with id: %s", id)
        return request.make_response(filecontent, headers)
