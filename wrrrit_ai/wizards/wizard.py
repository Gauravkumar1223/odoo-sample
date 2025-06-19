from odoo import models, fields, _


class WrrritWizardAiVoiceRecord(models.TransientModel):
    _name = "wrrrit.wizard.ai.voice.record"

    name = fields.Char(string="Name")

    def add_data(self):
        print("yessssss.................")
