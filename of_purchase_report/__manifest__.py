# -*- coding: utf-8 -*-

##############################################################################
#
#    OpenFire
#    Version OF10.0
#
#    Module conçu et développé par OpenFire SAS
#
#    Compatible avec Odoo 10 Community Edition
#
##############################################################################

{
    'name': u"OpenFire / Rapports d'achats",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "Purchases",
    'summary': u"OpenFire Purchase Reports",
    'description': u"""
Module OpenFire / rapports d'achats
===================================
Module OpenFire pour les rapports sur les achats.

Fonctionnalités
----------------
- Possibilité de sortir des rapports excel depuis le menu Achats > Rapports > Rapports de gestion :

  - Achats facturés non réceptionnés.
  - Achats réceptionnés non facturés.

- Possibilité de lier une ligne de facture à une commande fournisseur. Cela crée au besoin une ligne dans la commande.
- Possibilité de lier un mouvement de stock à une commande fournisseur. Cela crée au besoin une ligne dans la commande.
""",
    'depends': [
        'purchase',
        'stock_account',
    ],
    'data': [
        'views/of_purchase_report_views.xml',
        'wizards/of_purchase_report_wizard.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
