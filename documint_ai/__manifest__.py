# -*- coding: utf-8 -*-
{
    "name": "AI Writer",
    "description": """
        AI-powered tool for generating structured academic and technical content""",
    "summary": """
        DocuMint AI: Structured Content Generator
        =========================================
        Harness the power of AI for creating structured and high-quality content. Ideal for:

        - Academic courses and syllabi.
        - Theses and research papers.
        - Comprehensive technical documentation.
        - Adaptable for various writing themes.

        This tool simplifies and enhances the content creation process, 
        ensuring efficiency and quality in document production.
    """,
    "author": "frynol test",
    "website": "https://www.acceleate.com",
    "license": "LGPL-3",
    # Categories can be used to filter modules in modules listing
    "category": "Document Management",
    "version": "0.1",
    "application": True,
    "menu": True,
    "icon": "static/description/icon.png",
    # Dependencies necessary for this module to work correctly
    "depends": ["base", "mail", "bus"],
    # Always loaded
    "data": [
        "security/ir.model.access.csv",
        "views/mint_document_views.xml",
        "views/mint_chapter_views.xml",
        "views/mint_section_views.xml",
        "views/mint_settings_views.xml",
        "views/mint_menu.xml",
        "data/settings_data.xml",
        # Include any other data files your module may need
    ],
    # Only loaded in demonstration mode
    "demo": [
        "demo/demo.xml",
    ],
}
