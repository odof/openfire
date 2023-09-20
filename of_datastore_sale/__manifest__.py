# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': u"OpenFire / Connecteur ventes",
    'version': "10.0.2.0.0",
    'author': "OpenFire",
    'website': "http://www.openfire.fr",
    'category': "Openfire",
    'license': '',
    'summary': u"Openfire Connecteur commandes de vente",
    'description': u"""
Module OpenFire / Connecteur commandes de vente
===============================================

Module permettant la réception automatisée des commandes de vente depuis une base OpenFire.

/!\\\\ Information OpenFire :
Ce module nécessite l'installation de openerplib sur le serveur : sudo easy_install openerp-client-lib
""",
    'depends': [
        'of_sale',
        'stock_dropshipping',
        'of_datastore_common_sp',
    ],
    'data': [
        'data/of_sanitize_query.xml',
        'security/of_datastore_sale_security.xml',
        'security/ir.model.access.csv',
        'views/partner_views.xml',
        'views/sale_views.xml',
        'views/product_views.xml',
        'views/of_datastore_sale_views.xml',
        'views/purchase_views.xml',
        'hooks/post_hook.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
