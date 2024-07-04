# -*- coding: utf-8 -*-

{
    'name': "OpenFire / Prorata et factures de situation",
    'version': "10.0.1.1.0",
    'author': "OpenFire",
    'description': u"""
Commandes et factures avec compte prorata et retenue de garantie
================================================================

Ce module permet d'intégrer les charges de comptes prorata et les retenues de garantie aux bons de commandes.

Pour un fonctionnement correct, il convient de créer un produit :
 - de type Service
 - associé à un compte comptable de prorata (de classe 6)
 - dont la taxe à l'achat est renseignée
Il faut également créer un article de situation.
""",
    'website': "www.openfire.fr",
    'depends': [
        'sale',
        'of_sale_quote_template',
    ],
    'category': "OpenFire",
    'license': "",
    'data': [
        'report/of_situation_report.xml',
        'security/ir.model.access.csv',
        'views/of_sale_prorata_views.xml',
        'views/sale_order_views.xml',
        'wizards/wizard_situation_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
