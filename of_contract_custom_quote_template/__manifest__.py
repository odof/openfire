# -*- coding: utf-8 -*-

{
    "name": u"OpenFire / Module de lien entre contrat custom et modèles de devis",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    'license': 'AGPL-3',
    'summary': u"Ajout des contrats OpenFire",
    "description": u"""
Module de lien entre les contrats OpenFire et les modèles de devis
==================================================================
Factures
--------
 - Gestion du groupe des sections avancées pour la position de certains champs.

""",
    "website": "www.openfire.fr",
    "depends": [
        "of_contract_custom",
        "of_sale_quote_template",
    ],
    "category": "OpenFire",
    "data": [
        'views/account_views.xml',
        ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
