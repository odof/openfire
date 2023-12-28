# -*- coding: utf-8 -*-

{
    "name": "OpenFire / Types de devis",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    'license': 'AGPL-3',
    "category": "OpenFire",
    "description": u"""
Ajout des types de devis
========================
Type de devis
-------------
Création d'un nouveau modèle 'Type de devis' repris dans :
 - Devis/commandes
 - Modèles de devis
 - Factures

et utilisés dans les rapports :
 - Ventes > Rapport > Ventes
 - Ventes > Rapport > Tunnel quali
 - Ventes > Rapport > Tunnel quanti
 - Account > Rapports > Factures

""",
    "website": "www.openfire.fr",
    "depends": [
        "of_sale_quote_template",
        ],
    "data": [
        'reports/account_report_views.xml',
        'reports/sale_report_views.xml',
        'security/ir.model.access.csv',
        'views/account_views.xml',
        'views/of_sale_type_views.xml',
        'views/sale_views.xml',
        ],
    'installable': True,
    'application': False,
    'auto_install': False,
    }
