# -*- coding: utf-8 -*-
from odoo import fields, models, _
from bs4 import BeautifulSoup


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    def ag_remove_powered_by_odoo(self):
        powered_by = "<!-- POWERED BY -->"
        for record in self:
            if powered_by in str(record.body_html):
                body_html = record.body_html
                soup = BeautifulSoup(body_html, 'html.parser')
                powered_element = soup.find('td', attrs={'style': 'text-align: center; font-size: 13px;'})
                powered_element['style'] = 'text-align: center; font-size: 13px; display: none !important;'
                record.write({'body_html': str(soup)})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _('Templates have been cleaned up successfully'),
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'reload'
                }
            }
        }
