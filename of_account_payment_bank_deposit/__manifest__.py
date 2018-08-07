# -*- coding: utf-8 -*-

{
    'name' : "OpenFire Payment Bank Deposit",
    'version' : "10.0.1.0.0",
    'license': '',
    'author' : "OpenFire",
    'website' : "www.openfire.fr",
    'category': "Accounting",
    'summary': u"Allow bank deposit",
    'description': u"""
Module OpenFire - Payment Bank Deposit
======================================

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
