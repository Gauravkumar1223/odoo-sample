from odoo import models, fields, api


class ActionLogger(models.Model):
    _name = "action.logger"
    _description = "Log and track the status of long-running actions"

    name = fields.Char("Action Name")
    user_id = fields.Many2one(
        "res.users", string="User", default=lambda self: self.env.user
    )
    start_time = fields.Datetime("Start Time", default=fields.Datetime.now)
    end_time = fields.Datetime("End Time")
    duration = fields.Float("Duration (seconds)", compute="_compute_duration")
    status = fields.Selection(
        [
            ("pending", "Pending"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
            ("failed", "Failed"),
        ],
        default="pending",
    )
    tokens_generated = fields.Integer("Tokens Generated")
    cost = fields.Float("Cost")
    audio_record_duration = fields.Float("Audio Record Duration (seconds)")
    additional_info = fields.Text("Additional Information")

    @api.depends("start_time", "end_time")
    def _compute_duration(self):
        for record in self:
            if record.start_time and record.end_time:
                duration = (record.end_time - record.start_time).total_seconds()
                record.duration = duration
            else:
                record.duration = 0.0
