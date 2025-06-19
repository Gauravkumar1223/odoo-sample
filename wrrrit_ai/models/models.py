# -*- coding: utf-8 -*-
import asyncio
import logging
import os
import threading
import warnings


from datetime import datetime

from langchain.chains import VectorDBQA
from langchain.chat_models import ChatOpenAI
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma

from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
from .documents_ai_actions import DocumentAiActions
from .voice_record_ai_actions import VoiceRecordAiActions

import os

from odoo import http

import logging
import openai, base64
import tempfile
import mimetypes
import assemblyai as aai

from .wrrrit_knowledge import persist_directory


warnings.simplefilter("ignore")

_logger = logging.getLogger(__name__)


class AiReportPDF(models.Model):
    _name = "wrrrit.ai.voice_record.pdf"
    _description = "PDF Reports"

    name = fields.Char("Report Name", required=True, default="Report Name")
    pdf_report_data = fields.Binary("PDF File", attachment=True)
    voice_record_id = fields.Many2one(
        "wrrrit.ai.voice_record", string="Voice Record", ondelete="cascade"
    )
    grouped_voices_record_id = fields.Many2one(
        "wrrrit.ai.document", string="Group of Voice Records", ondelete="cascade"
    )
    medical_document_id = fields.Many2one(
        "wrrrit.ai.medical.document", string="Medical Document", ondelete="cascade"
    )


class GroupedAIDocuments(models.Model):
    _name = "wrrrit.ai.document"
    _description = "Vocal Group of Records"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char("Name", required=True)

    description = fields.Text("Description")
    email = fields.Char("Email", required=False)
    global_summary = fields.Text("Global Summary")
    global_translated_summary = fields.Text("Global Translated Summary")
    global_extract = fields.Text("Global Extract")
    global_report = fields.Binary(
        "Generated Global Report",
        attachment=True,
    )
    pdf_reports = fields.One2many(
        "wrrrit.ai.voice_record.pdf",
        "grouped_voices_record_id",
        string="Generated PDF Reports",
    )

    creation_date = fields.Date("Creation Date", default=fields.Date.context_today)
    owner_id = fields.Many2one("res.users", "Owner", default=lambda self: self.env.user)
    patient = fields.Many2one("res.partner", "Patient", help="Patient Name")

    patient_id = fields.Text("Patient ID", help="Patient ID")

    voice_record = fields.Binary("Medical Voice Record")
    file = fields.Binary("Voice  File", attachment=True)

    file_size = fields.Float("File Size (KB)", compute="action_calculate_size")
    active = fields.Boolean("Active", default=True)
    processing_requested = fields.Boolean("Processing Requested", default=True)

    computed_fields = fields.Text("Computed Fields")
    folder_id = fields.Many2one("wrrrit.ai.folder", string="Folder")
    document_type = fields.Selection(
        [
            ("medical_report", "Medical Report"),
            ("identification_document", "Identification Document"),
            ("medical_imagery", "Medical Imagery"),
            ("other", "Other"),
        ],
        string="Document Type",
        default="other",
    )

    record_locale = fields.Selection(
        [
            ("english", "Generate English"),
            ("german", "Generate German"),
            ("french", "Générer du Français"),
            ("italian", "Generare Italiano"),
            ("spanish", "Generar Español"),
            ("portuguese", "Gerar Português"),
            ("dutch", "Genereren in het Nederlands"),
            ("turkish", "Yazılımı Türkçe Yazة"),
            ("arabic", "توليد اللغة العربية"),
        ],
        string="Voice > Report Language",
        default="english",
    )
    is_user_admin = fields.Boolean(search="_search_is_user_admin")

    def _search_is_user_admin(self, operator, value):
        from odoo import _

        if operator not in ["=", "!="] or not isinstance(value, bool):
            raise UserError(_("Invalid search operator or value for is_user_admin"))
        is_true = (operator == "=" and value) or (operator != "=" and not value)
        user_is_admin = self.env.user.has_group("base.group_system")
        if (is_true and user_is_admin) or (not is_true and not user_is_admin):
            _logger.info("User is admin")
            return []  # Return an empty domain to match all records
        else:
            _logger.info("User is not admin")
            return [("id", "=", 0)]  # Return a domain to match no records

    voice_record_ids = fields.One2many(
        "wrrrit.ai.voice_record", "document_id", string="Voice Records"
    )
    report_template = fields.Many2one(
        "wrrrit.ai.report", string="Report Template"
    )  # New field
    custom_ai_sections = fields.Text("Custom AI Sections")
    medical_document_ids = fields.One2many(
        "wrrrit.ai.medical.document", "medical_document_id", string="Medical Documents"
    )

    @api.model
    def create(self, vals):
        record = super(GroupedAIDocuments, self).create(vals)
        return record

    def action_open_voice_record_form(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "wrrrit.ai.voice_record",
            "view_mode": "form",
            "view_id": self.env.ref("ai_wrrrit.wrrrit_ai_voice_record_form").id,
            "target": "new",
            "context": {"default_document_id": self.id},
        }

    def action_add_voice_record(self, vals):
        self.ensure_one()
        self.write({"voice_record_ids": [(0, 0, vals)]})

    def action_remove_voice_record(self, record_id):
        self.ensure_one()
        self.write({"voice_record_ids": [(2, record_id)]})

    def action_unarchive(self):
        self.active = True

    def action_compute_meta(self):
        doc_ai = DocumentAiActions()
        doc_ai.action_compute_meta(self)

    def action_translate_meta(self):
        doc_ai = DocumentAiActions()
        doc_ai.action_translate_meta(self)

    def action_global_summarize(self):
        for record in self:
            try:
                _logger.info(
                    f"Processing record ID {record.id} for global summarization."
                )
                global_summary = ""

                if record.voice_record_ids:
                    _logger.info(f"Processing vocal records for record ID {record.id}.")
                    for vr in record.voice_record_ids:
                        try:
                            last_updated = (
                                vr.last_updated.strftime("%Y-%m-%d %H:%M")
                                if vr.last_updated
                                else "Unknown Date"
                            )
                            transcription_data = (
                                vr.transcription_data
                                if vr.transcription_data
                                else "No transcription data"
                            )
                            global_summary = (
                                global_summary
                                + "\n\n Last Updated: \n"
                                + last_updated
                                + "\n\n"
                                + transcription_data
                            )
                            _logger.info(
                                f"Successfully processed vocal record ID {vr.id} for record ID {record.id}."
                            )
                        except Exception as e:
                            # Logging the exception for better debugging
                            _logger.error(
                                f"Error processing voice record ID {vr.id}: {e}"
                            )

                if record.medical_document_ids:
                    _logger.info(
                        f"Processing medical documents for record ID {record.id}."
                    )
                    for md in record.medical_document_ids:
                        try:
                            global_summary = global_summary + "\n\n" + md.description
                            _logger.info(
                                f"Successfully processed medical document ID {md.id} for record ID {record.id} : "
                            )
                        except Exception as e:
                            # Logging the exception for better debugging
                            _logger.error(
                                f"Error processing medical document ID {md.id}: {e}"
                            )

                record.global_summary = global_summary
                _logger.info(
                    f"Successfully updated global summary for record ID {record.id}."
                    + f"\n{global_summary}"
                )

            except Exception as e:
                # Logging the outer exception
                _logger.error(f"Error processing record ID {record.id}: {e}")
                record.global_summary = "No Global Summary"

    def action_global_translate(self):
        _logger.info("Groupping All VR Translations action_global_translate")
        for record in self:
            try:
                global_translated = ""
                if record.voice_record_ids:
                    for vr in record.voice_record_ids:
                        try:
                            last_updated = (
                                vr.last_updated.strftime("%Y-%m-%d %H:%M")
                                if vr.last_updated
                                else "Unknown Date"
                            )
                            translated_data = (
                                vr.translated_data
                                if vr.translated_data
                                else "No translated data"
                            )
                            global_translated = (
                                global_translated
                                + "\n\n Last Updated: \n"
                                + last_updated
                                + "\n\n"
                                + translated_data
                            )
                        except Exception as e:
                            # Logging the exception for better debugging
                            print(f"Error processing voice record ID {vr.id}: {e}")
                    record.global_translated_summary = global_translated
            except Exception as e:
                # Logging the outer exception
                print(f"Error processing record ID {record.id}: {e}")

    def action_global_extract(self):
        doc_ai = DocumentAiActions()
        doc_ai.action_global_extract(self)

    def action_global_report(self):
        doc_ai = DocumentAiActions()
        doc_ai.action_global_extract(self)

    def action_global_drugs_diseases(self):
        pass


class AiFolder(models.Model):
    _name = "wrrrit.ai.folder"
    _description = "MED AI Folder"

    name = fields.Char("Folder Name", required=True)
    parent_id = fields.Many2one("wrrrit.ai.folder", string="Parent Folder")
    child_ids = fields.One2many("wrrrit.ai.folder", "parent_id", string="Child Folders")
    document_ids = fields.One2many(
        "wrrrit.ai.document", "folder_id", string="Documents"
    )

    def unlink(self):
        if self.child_ids or self.document_ids:
            raise ValidationError(
                "You cannot delete a folder that contains other folders or documents."
            )
        return super().unlink()

    def action_rename(self, new_name):
        self.name = new_name
