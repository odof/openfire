# -*- coding: utf-8 -*-

{
    'name': u"OpenFire / Stock partagé entre magasins",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'summary': u"ATTENTION : à installer pour partager des stocks uniquement, voir détails",
    'description': u"""
ATTENTION : Ce module doit uniquement être installé pour partager les stocks entre plusieurs magasins !
=======================================================================================================

Ne pas oublier de bien configurer le champ "Est le propriétaire du stock" de chaque société et magasin avant installation.
--------------------------------------------------------------------------------------------------------------------------

Rappel : Ce champ permet de définir la société comme propriétaire du stock de toutes ses sociétés enfant, c'est à dire
que chaque société enfant pourra partager son stock avec ses sociétés soeurs.

Personnalisation Stock partagé entre magasins :

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
