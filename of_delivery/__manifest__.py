# -*- coding: utf-8 -*-

{
    'name': "OpenFire / Frais de livraisons",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "Generic Modules",
    'summary': u"Gestion des frais de livraisons",
    'description': u"""
OpenFire frais de livraisons :
==============================

ATTENTION : Il faut définir une marque et une catégorie par défaut pour les articles.
_____________________________________________________________________________________

- Ajout de l'utilisation des franco de port sur les demandes de prix/commandes fournisseurs.


""",
    'depends': [
        'delivery',
        'of_sale',
    ],
    'data': [
        'views/delivery_carrier_views.xml',
        'views/purchase_order_views.xml',
        'views/stock_picking_views.xml',
        'reports/report_deliveryslip.xml',
        ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
