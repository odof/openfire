# -*- coding: utf-8 -*-

{
    'name': u"OpenFire / Stock multi-sociétés",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'description': u"""
Personnalisation Stock multi-sociétés :

- Modification des domain sur les ir.rule suivantes: stock_warehouse_comp_rule, stock_picking_type_rule, stock_quant_rulestock.warehouse.
- Passage de company_id a la plus société parente la plus haute sur les emplacements, entrepots, quant et routes
- Message d'erreur sur les tentatives de modification du champ company_id
""",
    'website': "www.openfire.fr",
    'depends': [
        'of_base_multicompany',
        'of_stock',
        'of_account_boutique',
    ],
    'category': "OpenFire",
    'data': [
        'data/ir_rule.xml',
        'data/auto_init.xml',
        'views/stock_views.xml',
        'views/account_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
