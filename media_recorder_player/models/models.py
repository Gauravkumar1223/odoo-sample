# -*- coding: utf-8 -*-
import base64
import logging

from odoo import models, fields, api

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)


class MediaRecording(models.Model):
    _name = 'media.recorder'
    _description = 'Media Recorder'

    name = fields.Char(string='Title', default='New Recording', required=True)
    recording_date = fields.Datetime(string='Recording Date', default=fields.Datetime.now)
    duration = fields.Float(string='Duration (seconds)')
    type = fields.Selection([
        ('audio', 'Audio'),
        ('screen', 'Screen Capture')
    ], string='Type', default='audio', required=True)
    file = fields.Binary(string='Recording File', attachment=True)
    audio_file = fields.Binary(string='Audio File', attachment=True)
    audio_file_name = fields.Char(string='Audio File Name')
    patient_id = fields.Many2one('res.partner', string='Patient')
    patient_name = fields.Char(string='Patient Name')
    doctor_id = fields.Many2one('res.partner', string='Doctor')
    doctor_name = fields.Char(string='Doctor Name')
    # audio_attachments = fields.Many2many('ir.attachment', string='Audio Attachments')
    # medical_attachments = fields.Many2many('ir.attachment', string='Medical Attachment')
    # document_attachments = fields.Many2many('ir.attachment', string='Document Attachment')
    # report_pdf_attachments = fields.Many2many('ir.attachment', string='Report Attachment')
    # image_attachments = fields.Many2many('ir.attachment', string='Image Attachment')
    # video_attachments = fields.Many2many('ir.attachment', string='Video Attachment')
    # other_attachments = fields.Many2many('ir.attachment', string='Other Attachment')


    transcript = fields.Text(string='Transcript')

    reviewed = fields.Boolean(string='Reviewed', default=False)
    revised_transcript = fields.Text(string='Revised Transcript')
    extracted_data = fields.Text(string='Extracted Data')
    extracted_data_json = fields.Text(string='Extracted Data JSON')
    extracted_data_json_file = fields.Binary(string='Extracted Data JSON File', attachment=True)
    extracted_data_json_file_name = fields.Char(string='Extracted Data JSON File Name')


    user_id = fields.Many2one('res.users', string='Recorded By', default=lambda self: self.env.user)
    locale = fields.Char(string='Locale', default=lambda self: self.env.user.lang)



    @api.model
    def save_recording(self, record_id, base64data):
        try:
            # Convert base64 string to binary data
            audio_data = base64.b64decode(base64data.split(',')[1])

            record = self.browse(record_id)
            if record:
                # Update the existing record
                _logger.info('Updating existing record %s', record_id)
                record.write({'file': audio_data, 'name': 'Updated ' + record.name})
            else:
                # Create a new record
                _logger.info('Creating new record %s', record_id)
                self.create({'file': audio_data, 'name': 'New Recording'})

        except Exception as e:
            _logger.error('Error saving recording: %s', str(e))
            # Optionally, re-raise the exception if you want it to be propagated
            raise


class MediaSettings(models.Model):
    _name = 'media.settings'
    _description = 'Media Recorder/Player Settings'

    quality = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ], string='Quality', default='medium', required=True)
    auto_save = fields.Boolean(string='Auto Save', default=True)
    format = fields.Selection([
        ('mp3', 'MP3'),
        ('mp4', 'MP4'),
        ('wav', 'WAV')
    ], string='Format', default='mp3', required=True)
    auto_play = fields.Boolean(string='Auto Play', default=True)


class MediaReportTemplate (models.Model):
    _name = 'media.report.template'
    _description = 'Media Report Template'

    name = fields.Char(string='Name', required=True)
    template = fields.Html(string='Template', required=True)
    active = fields.Boolean(string='Active', default=True)
    type = fields.Selection([
        ('audio', 'Audio'),
        ('document', 'Document Capture')
    ], string='Type', default='audio', required=True)
    user_id = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user)
    locale = fields.Char(string='Locale', default=lambda self: self.env.user.lang)
