# -*- coding: utf-8 -*-

{
    "name": "OpenFire / Planning website",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    'category': 'OpenFire modules',
    'summary': 'Planning website',
    'license': 'LGPL-3',
    "description": """
Ce module permet à des utilisateurs portail de prendre RDV depuis le site web.
""",
    "website": "www.openfire.fr",
    "depends": [
        "of_planning_tournee",
        "of_website_portal",
        "of_parc_chem",
        "auth_signup",
    ],
    "data": [
        'views/of_planning_website_views.xml',
        'views/of_planning_website_templates.xml',
        'security/ir.model.access.csv',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'installable': True,
    'application': False,
}
