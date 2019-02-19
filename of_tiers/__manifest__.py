# -*- coding: utf-8 -*-

{
    'name' : 'OpenFire / Comptes de tiers',
    'version' : '10.0.1.0.0',
    'summary': 'Utilisation de comptes de tiers pour les clients et fournisseurs',
    'description': """
OpenFire / Comptes de tiers
===========================
Utilisation de comptes de tiers
    """,
    'category': 'Accounting',
    'depends' : ['account'],
    'data': [
        'views/of_tiers_view.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
