# -*- coding: utf-8 -*-

{
    "name": "OpenFire / RDV commercial",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    'license': '',
    "category": "OpenFire",
    "description": """
Prise de RDV commercial OpenFire
================================

- Ajout de la prise de rdv commercial depuis les partenaires et les opportunités

""",
    "website": "www.openfire.fr",
    "depends": [
        "of_calendar",
        "of_sale",
        "of_crm",
        "of_base",
    ],
    "data": [
        'wizards/of_rdvcom_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
