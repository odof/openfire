# -*- coding: utf-8 -*-
{
    'name': "OpenFire / Ventes en boutique",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'license': '',
    'website': "www.openfire.fr",
    'category': "Generic Modules/Accounting",
    'description': u"""
Module de vente en boutique OpenFire.
=====================================

Permettre la création de facture en mode "boutique".
Une facture en mode boutique génére un bon de livraison validé lors du passage en état ouverte.

Comptabilité:
-------------
 - Ajout d'un menu 'Factures Boutiques' pour permettre la création de facture en mode "boutique"
 - Ajout d'un smart button affichant les bons de livraisons liés à une facture

""",
    'depends': [
        'of_account',
        'stock',
    ],
    'demo_xml': [],
    'data': [
        'views/of_account_boutique_views.xml',
    ],
    'installable': True,
}
