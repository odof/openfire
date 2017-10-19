# -*- coding: utf-8 -*-

{
    'name' : 'OpenFire Payment Modes',
    'version' : '10.0.1.0.0',
    'summary': 'Use distinct payment modes within journals',
    'description': """
OpenFire Payment Modes
======================
    """,
    'category': 'Accounting',
    'depends' : ['account'],
    'data': [
        'views/of_account_payment_mode_view.xml',
        'security/ir.model.access.csv',
        'security/of_account_payment_mode_security.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
