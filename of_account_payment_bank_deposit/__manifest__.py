# -*- coding: utf-8 -*-

{
    'name' : "OpenFire / Remises en banque",
    'version' : "10.0.1.0.0",
    'license': '',
    'author' : "OpenFire",
    'website' : "www.openfire.fr",
    'category': "Accounting",
    'summary': u"Remises en banque",
    'description': u"""
Module OpenFire / Remises en banque
===================================

Fonctionnalités
----------------
- Permettre l'impression de bordereaux de remise en banque

""",
    'depends' : [
        'account',
    ],
    'data' : [
        'views/of_account_payment_bank_deposit_view.xml',
        'security/ir.model.access.csv',
        'reports/of_rapport_remise_banque.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
