# -*- coding: utf-8 -*-

{
    "name": "OpenFire / Demande d'intervention - Modes de paiement",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    'license': 'AGPL-3',
    'summary': u"Module de lien entre demandes d'intervention et mode de paiement",
    "description": u"""
OpenFire / Demande d'intervention - Modes de paiement
=====================================================

Module de lien entre les modules of_service et of_mode_paiement

""",
    "website": "www.openfire.fr",
    "depends": [
        "of_service",
        "of_mode_paiement",
    ],
    "category": "OpenFire",
    "data": [
        'security/ir.model.access.csv',
        'security/of_service_mode_paiement_security.xml',
        'views/of_service_views.xml',
        'views/of_paiement_edi_views.xml',
        'views/of_intervention_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
