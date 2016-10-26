# -*- coding: utf-8 -*-

{
    'name' : 'OpenFire Payment Modes',
    'version' : '1.1',
    'summary': 'Use distinct payment modes within journals',
    'sequence': 30,
    'description': """
OpenFire Payment Modes
======================
    """,
    'category': 'Accounting',
    'depends' : ['account'],
    'data': [
        'views/of_account_payment_mode_view.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [ ],
    'qweb': [ ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
