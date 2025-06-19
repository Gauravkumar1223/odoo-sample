import datetime

from odoo import models, fields, api
from odoo.exceptions import UserError


class PromptTemplate(models.Model):
    _name = "wrrrit.ai.prompt"
    _description = "Wrrrit Prompt Template"

    name = fields.Char("Report Name", required=True)
    prompt_prefix = fields.Text("Prompt Prefix")
    prompt_postfix = fields.Text("Prompt Postfix")
    prompt_sections = fields.Text("Raw Sections")
    section_ids = fields.Many2many("wrrrit.ai.prompt.section", string="Sections")
    create_date = fields.Datetime(string="Creation Date", default=fields.Datetime.now)
    insert_date = fields.Boolean(string="Insert Date", default=True)
    insert_locale = fields.Boolean("Translate Locale", default=True)
    insert_owner = fields.Boolean("Insert Owner", default=True)
    ai_model = fields.Text("AI Model", default="gpt-3.5-turbo")
    is_user_admin = fields.Boolean(
        compute="_compute_is_user_admin", search="_search_is_user_admin"
    )

    @api.depends()
    def _compute_is_user_admin(self):
        for record in self:
            record.is_user_admin = self.env.user.has_group("base.group_system")

    def _search_is_user_admin(self, operator, value):
        if operator == "=" and value:
            return [("create_uid", "=", self.env.user.id)]
        return []

    @staticmethod
    def system_prompt_builder(self):
        date_of_day = datetime.datetime.now().strftime("%Y-%m-%d")
        system_prompt = f"Today is :" + date_of_day + f"\n"
        system_prompt = system_prompt + self.prompt_prefix + "\n"
        system_prompt = system_prompt + self.prompt_sections + "\n"
        system_prompt = system_prompt + self.prompt_postfix + "\n"

        return system_prompt
