# -*- coding: utf-8 -*-

{
    "name": "OpenFire / Planning View",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    'category': 'OpenFire modules',
    'summary': 'Planning View',
    'license': 'LGPL-3',
    "description": """

""",
    "website": "www.openfire.fr",
    "depends": [
        "of_planning_tournee",
    ],
    "data": [
        "views/of_planning_view_views.xml",
        "views/of_planning_view_templates.xml",
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'installable': True,
    'application': False,
}
