# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.osv import expression


class ReportTemplate(models.Model):
    _name = "wrrrit.ai.report"
    _description = "Wrrrit Report Template"

    name = fields.Char("Report Name", required=True)
    header = fields.Text("Header")
    footer = fields.Text("Footer")
    template_definition = fields.Text("Sections")
    logo = fields.Binary("Logo")
    style = fields.Text("CSS Style")
    color_scheme = fields.Selection(
        [
            ("blue", "Blue"),
            ("green", "Green"),
            ("red", "Red"),
        ],
        string="Color Scheme",
    )

    @api.model
    def _get_default_prompt_template(self):
        return self.env["wrrrit.ai.prompt"].search([], limit=1).id

    prompt_template_id = fields.Many2one(
        "wrrrit.ai.prompt",
        string="Prompt Template",
        help="Select the prompt template associated with this report template.",
        default=_get_default_prompt_template,
    )

    @api.model
    def search_options(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = expression.AND([[('name', operator, name)], args])
        template_ids = self._search(domain, limit=limit, access_rights_uid=name_get_uid)
        templates = self.browse(template_ids)
        options = []
        for template in templates:
            options.append(
                {
                    "id": template.id,
                    "name": template.name,
                    "prompt_template": template.prompt_template_id.name,
                    "color_scheme": template.color_scheme,
                    "logo": template.logo,
                }
            )
        return options


#
