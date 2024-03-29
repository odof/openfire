# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "OpenFire / Demande d'intervention - Achats",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    'license': 'AGPL-3',
    'summary': u"Module de lien entre demandes d'intervention et achats",
    "description": u"""
OpenFire / Demande d'intervention - Achats
==========================================

Module de lien entre les modules of_service et of_purchase

""",
    "website": "www.openfire.fr",
    "depends": [
        "of_service",
        "of_purchase",
        ],
    "category": "OpenFire",
    "data": [
        'views/of_service_views.xml',
        'views/purchase_views.xml',
        'wizard/of_make_po_validation_wizard_views.xml',
        ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
