# -*- coding: utf-8 -*-

{
    "name": "OpenFire Web Widgets",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    'category': 'OpenFire modules',
    'summary': 'Web Widgets',
    'license': 'AGPL-3',
    "description": """
Module OpenFire de widgets
==========================

""",
    "website": "www.openfire.fr",
    "depends": ["web", "web_kanban"],
    "data": [
        "views/of_web_widgets_templates.xml",
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
