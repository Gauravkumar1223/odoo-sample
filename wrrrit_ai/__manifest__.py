# -*- coding: utf-8 -*-
{
    "name": "Wrrrit Assistant",
    "application": True,
    "menu": True,
    "summary": """
     Vocal AI Assistant for Doctors and Practicians
    """,
    "author": "frynol test",
    "license": "LGPL-3",
    "version": "0.1",
    "website": "https://www.acceleate.com",
    "category": "Services",
    #    'icon': 'static/src/img/icon.png',
    # any module necessary for this one to work correctly
    "depends": ["base", "mail", "bus"],
    # always loaded
    "data": [
        "views/views.xml",
        "views/templates.xml",
        "views/wrrrit_report_view.xml",
        "views/view_voice_record.xml",
        "views/wrrrit_knowledge.xml",
        "views/medical_document.xml",
        "views/prompt_template.xml",
        "data/security.xml",
        "security/ir.model.access.csv",
        "data/data.xml",
        "data/wrrrit_sections_data.xml",
        "data/wrrrit_cardiology_report.xml",
        "data/wrrrit_dermatology_report.xml",
        "data/wrrrit_psychology_report.xml",
        "data/wrrrit_patient_report.xml",
        "data/wrrrit_patient_detailed_report.xml",
        "data/wrrrit_psy_detailed.xml",
        "data/cardiology_report_template.xml",
        "data/cardio_echo_report_template.xml",
        "data/annual_medical_report.xml",
        "data/general_medecine_report.xml",
        "wizards/wizard.xml",
        "views/sections_front_end.xml",
    ],
    # only loaded in demonstration mode
    "demo": [],
    "assets": {
        "web.assets_backend": [
            # Qweb files
            "/wrrrit_ai/static/src/xml/wrrrit_context_menu.xml",
            "/wrrrit_ai/static/src/xml/wrrrit_refresh.xml",
            "/wrrrit_ai/static/src/xml/wrrrit_voice_record.xml",
            "/wrrrit_ai/static/src/xml/wrrrit_docx_viewer.xml",
            "/wrrrit_ai/static/src/xml/wrrrit_ai_record_odoo.xml",
            "/wrrrit_ai/static/src/xml/wrrrit_realtime_textarea.xml",
            "/wrrrit_ai/static/src/xml/wrrrit_long_task_widget.xml",

            # SCSS files
            "/wrrrit_ai/static/src/scss/wrrrit_ai.scss",

            # CSS files
            # "/wrrrit_ai/static/src/css/wrrrit_ai.css",

            # JS files
            "/wrrrit_ai/static/src/js/wrrrit_ai_widget.js",
            # '/wrrrit_ai/static/src/js/wrrrit_ai_record_odoo.js',
            "/wrrrit_ai/static/src/js/recorder.js",
            "/wrrrit_ai/static/src/js/wrrrit_ai_record.js",
            "/wrrrit_ai/static/src/js/wrrrit_context_menu.js",
            # "/wrrrit_ai/static/src/js/wrrrit_voice_recorder_widget.js",
            "/wrrrit_ai/static/src/js/wrrrit_truncate_widget.js",
            "/wrrrit_ai/static/src/js/wrrrit_refresh.js",
            "/wrrrit_ai/static/src/js/wrrrit_docx_viewer.js",
            "/wrrrit_ai/static/src/js/wrrrit_realtime_textarea.js",
            "/wrrrit_ai/static/src/js/wrrrit_notification.js",
            "/wrrrit_ai/static/src/js/wrrrit_long_task_button.js",
            "/wrrrit_ai/static/src/js/wrrrit_long_task_widget.js",

        ],
        "web_assets_frontend": [],
    },
}
