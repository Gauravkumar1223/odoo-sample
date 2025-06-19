# -*- coding: utf-8 -*-
# Copyright (C) 2022 - Auguria (<https://www.auguria.fr>).
{
    'name': 'Remove Powered By Odoo',
    'version': '16.0.3',
    'author': 'Auguria SAS',
    'license': 'LGPL-3',
    'category': 'Email',
    'website': 'https://www.auguria.fr',
    'images': ['static/description/banner.png'],
    'summary': 'Remove Powered By Odoo',
    'description': """Remove power by odoo on footer of emails and the website""",
    'depends': ['base', 'mail', 'web'],
    'data': [
        'views/mail_template_remove_odoo_views.xml',
        'views/website_footer_brand_promotion.xml'
    ],
    'installable': True,
    'support': 'contact@auguria.fr',
    'application': True,
}
