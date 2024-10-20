# -*- coding: utf-8 -*-

{
    'name': u"OpenFire / Base multi-sociétés",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'complexity': "easy",
    # Réduction de la séquence pour permettre un chargement avant celui des autres modules (à réduire encore au besoin)
    'sequence': 40,
    'description': u"""
Personnalisation multi-sociétés :

- Les champs company-dependent se lisent au niveau de la société comptable au lieu de la société courante.
- Modification des droits pour permettre l'utilisation de la configuration comptable des sociétés parentes.
- La société des comptes comptables est forcée au niveau d'une société comptable.
- Modification des droits pour permettre la manipulation d'éléments comptables de la société comptable.
""",
    'website': "www.openfire.fr",
    'depends': [
        'account',
        'account_reversal',
        'sale_stock',
        'stock_account',
    ],
    'category': "OpenFire",
    'data': [
        'security/of_base_multicompany_security.xml',
        'views/account_invoice_view.xml',
        'views/account_payment_view.xml',
        'views/res_company_view.xml',
        'views/res_config_view.xml',
        'views/sale_order_view.xml',
    ],
    'qweb': [
        'static/src/xml/of_base_multicompany.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
