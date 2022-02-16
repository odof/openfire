# -*- coding: utf-8 -*-

{
    'name': u"OpenFire / Stock multi-sociétés",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'description': u"""
Personnalisation Stock multi-sociétés :

- Modification des domain sur les ir.rule suivantes : stock_warehouse_comp_rule, stock_picking_type_rule, stock_quant_rule
- Passage de company_id à la société propriétaire des stocks sur les emplacements, entrepôts et quant
- Message d'erreur sur les tentatives de modification du champ company_id
""",
    'website': "www.openfire.fr",
    'depends': [
        'of_base_multicompany',
        'of_stock',
        'of_account_boutique',
        'of_planning',
    ],
    'category': "OpenFire",
    'data': [
        'data/auto_init.xml',
        'security/of_stock_multicompany_security.xml',
        'views/stock_views.xml',
        'views/account_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
