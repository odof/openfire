{
    'name': "OpenFire / SMS sale",
    'version': "16.0.0.0.0",
    'author': "OpenFire",
    'license': 'LGPL-3',
    'website': "www.openfire.fr",
    'category': "Generic Modules/",
    'description': u"""
Module de SMS OpenFire pour les ventes
======================================

- Envoi de SMS depuis les ventes instantanément ou en différé
""",
    'depends': [
        'of_sms',
        'of_sale',
    ],
    'demo_xml': [],
    'data': [
        'views/sale_order_views.xml',
    ],
    'installable': True,
}
