from odoo import models, fields, api


class BackgroundAction(models.Model):
    _name = "background.action"
    _description = "Background Action"

    name = fields.Char("Action Name")
    user_id = fields.Many2one("res.users", "User", default=lambda self: self.env.user)
    start_time = fields.Datetime("Start Time", default=fields.Datetime.now)
    end_time = fields.Datetime("End Time")
    duration = fields.Float("Duration (seconds)", compute="_compute_duration")
    status = fields.Selection(
        [
            ("pending", "Pending"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
        default="pending",
    )
    result = fields.Text("Result")
    additional_info = fields.Text("Additional Information")

    @api.depends("start_time", "end_time")
    def _compute_duration(self):
        for record in self:
            if record.start_time and record.end_time:
                record.duration = (record.end_time - record.start_time).total_seconds()
            else:
                record.duration = 0
