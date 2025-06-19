# -*- coding: utf-8 -*-
{
    'name': "Media Recorder/Player",

    'summary': """
        A versatile tool for recording audio and screen capturing from browser media APIs""",

    'description': """
        Media Recorder/Player is designed to facilitate easy and efficient recording of audio and 
        screen capture using browser media APIs. Aimed at providing a user-friendly interface and 
        robust functionality for media recording and playback, this module is ideal for various 
        applications in media management and content creation.""",

    'author': "frynol test",
    'website': "http://www.acceleate.com",
    "application": True,
    "menu": True,

    'category': 'Multimedia',
    'version': '0.1',
    'license': 'LGPL-3',

    'depends': ['base', 'web'],

    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'media_recorder_player/static/src/components/*/*.js',
            'media_recorder_player/static/src/components/*/*.xml',
            'media_recorder_player/static/src/components/*/*.scss',
            'media_recorder_player/static/src/components/*/*.css',

        ]

    },
    'js': [

        '/media_recorder_player/static/lib/wavesurfer.js/dist/wavesurfer.js',
        '/media_recorder_player/static/lib/wavesurfer.js/dist/plugin/renderer.js',

    ],

    'demo': [
    ],
}
