{
    'name': 'frynol_rag',
    'version': '1.0.0',
    'category': 'Q_A management',
    'author':'Python Team',
    'sequence': "-100",
    'summary': 'Upload files and query on it',
    'description': "Upload files and query on it",
    'depends':[],
    'data':[
        'security/ir.model.access.csv',
        'views/menu.xml',
        'views/template.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # 'frynol_rag/static/src/js/assets.js',
            # 'frynol_rag/static/src/xml/assets.xml',
            'frynol_rag/static/src/js/realtime.js',
            'frynol_rag/static/src/xml/realtime.xml',
            # 'frynol_rag/static/src/js/audio.js',
            # 'frynol_rag/static/src/xml/audio.xml',
            # 'frynol_rag/static/src/scss/assets.scss',
            'frynol_rag/static/src/scss/realtime.scss',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application':True,
    'license': 'LGPL-3'
}
