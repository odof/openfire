# -*- coding: utf-8 -*-
{
    "name" : "OpenFire / Comptabilité",
    "version" : "0.9",
    "author" : "OpenFire",
    "website" : "www.openfire.fr",
    "category" : "Generic Modules/Sales & Purchases",
    "description": """
Module de comptabilité OpenFire.
======================================

Ce module apporte une personnalisation de la comptabilité :

- Fonctions pratiques pour la saisie des écritures comptables
- Fusion de factures brouillon sous condition, sans fusionner les lignes
""",
    "depends" : [
        'account',
    ],
    "demo_xml" : [ ],
    'data': [
        'views/of_account_view.xml',
        'wizard/wizard_invoice_group_view.xml',
    ],
    "installable": True,
    'active': False,
}
# vim:expandtab:smartindent:tabstop=4:sorderttabstop=4:shiftwidth=4:
