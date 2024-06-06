# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': u"OpenFire / Réservation de Stock pour les Ventes",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'license': 'AGPL-3',
    'category': u"OpenFire",
    'website': u"www.openfire.fr",
    'description': u"""
Réservation de Stock pour les Ventes :
--------------------------------------

Module permettant la réservation d'articles en stock depuis les commandes de ventes.
""",
    'website': "www.openfire.fr",
    'depends': [
        'stock_reserve',
        'of_kit',
        'of_sale_stock',
    ],
    'category': "OpenFire",
    'data': [
        'data/data.xml',
        'wizards/of_stock_reserve_sale_wizard_views.xml',
        'views/sale_order_views.xml',
        'views/stock_picking_views.xml',
        'views/stock_reserve_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
