from odoo import models, fields


class MintSection(models.Model):
    _name = "mint.section"
    _description = "DocuMint AI Section"
    _order = "sequence"

    name = fields.Char(string="Title")
    chapter_id = fields.Many2one("mint.chapter", string="Chapter")
    parent_id = fields.Many2one("mint.section", string="Parent Section")
    child_ids = fields.One2many("mint.section", "parent_id", string="Subsections")
    sequence = fields.Integer(string="Sequence")
    locale = fields.Char(string="Locale", default="english")
    content = fields.Text(string="Content Title")
    content_generated = fields.Text(string="Generated Content")
    prompt = fields.Text(string="Prompt")
    tokens_generated = fields.Integer(string="Tokens Generated")
    style_metadata = fields.Text(string="Style Metadata")
