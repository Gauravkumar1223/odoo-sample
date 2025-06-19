from odoo import models, fields, api


class Section(models.Model):
    _name = "wrrrit.ai.prompt.section"
    _description = "Wrrrit AI Prompt Section"

    title = fields.Char("Section Title", required=True)
    prompt = fields.Text("Section AI Prompt")
    extra = fields.Text("Section Formatting")
    style = fields.Html("Section Style", sanitize=False)
    sequence = fields.Integer("Sequence", default=10)
    prompt_template_ids = fields.Many2many(
        "wrrrit.ai.prompt", string="Prompt Templates"
    )

    @api.depends("sequence", "title")
    def name_get(self):
        result = []
        for record in self:
            name = "{} - {}".format(record.sequence, record.title)
            result.append((record.id, name))
        return result
