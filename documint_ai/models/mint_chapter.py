from odoo import models, fields


class MintChapter(models.Model):
    _name = "mint.chapter"
    _description = "DocuMint AI Chapter"
    _order = "sequence"

    name = fields.Char(string="Name")
    title = fields.Char(string="Title")
    content = fields.Text(string="Content")
    document_id = fields.Many2one("mint.document", string="Document")
    sequence = fields.Integer(string="Sequence")
    locale = fields.Char(string="Locale", default="English")
    section_ids = fields.One2many("mint.section", "chapter_id", string="Sections")
    content_generated = fields.Text(string="Generated Content")
    prompt = fields.Text(string="Prompt")
    tokens_generated = fields.Integer(string="Tokens Generated")
    style_metadata = fields.Text(string="Style Metadata")
