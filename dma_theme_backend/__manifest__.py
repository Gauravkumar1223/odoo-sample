# -*- coding: utf-8 -*-
# Developed by Mathieu Pittiloni
# See LICENSE file for full copyright and licensing details
{
    'name': 'frynol Backend Theme',
    'category': 'Themes/Backend',
    'version': '1.0',
    "author": "Mathieu Pittiloni",
     "maintainers": ["Mathieu Pittiloni"],
    "website": "https://www.direct-medical.net",
    'summary': 'The frynol Odoo Backend theme.',
    'description': """ The frynol Odoo Backend theme.""",
    'depends': ['web', 'base_setup', 'portal', 'resource'],
    'assets': {
        'web.assets_backend': [
            # Qweb files
            "/frynol_theme_backend/static/src/xml/nav_bar.xml",
            "/frynol_theme_backend/static/src/xml/record_file_field.xml",
            "/frynol_theme_backend/static/src/xml/many2one_image_field.xml",

            # scss files
            "/frynol_theme_backend/static/src/scss/main_view.scss",
            "/frynol_theme_backend/static/src/scss/many2one_image_field.scss",

            # js files
            "/frynol_theme_backend/static/src/js/record_file_field.js",
            "/frynol_theme_backend/static/src/js/many2one_image_field.js",
        ],
        'web.assets_frontend': [
        ],
    },
    'sequence': 1,
    'installable': True,
    'application': True,
    'license': 'OPL-1',
    'currency': 'EUR',
}
