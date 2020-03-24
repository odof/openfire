# -*- coding: utf-8 -*-

{
    "name": "OpenFire / Planning view",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    'category': 'OpenFire modules',
    'summary': 'Planning view',
    'license': 'LGPL-3',
    "description": """
Ajout de la vue PLanning.
""",
    "website": "www.openfire.fr",
    "depends": [
        "of_planning_tournee",
        "of_utils",
    ],
    "data": [
        "views/of_planning_view_views.xml",
        "views/of_planning_view_templates.xml",
        "wizard/planification_views.xml",
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'installable': True,
    'application': False,
}
