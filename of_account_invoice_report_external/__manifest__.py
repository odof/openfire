# -*- coding: utf-8 -*-

{
    'name': u'OpenFire / Impression factures - en-tête externe',
    'author': 'OpenFire',
    'version': '10.0.1.0.0',
    'category': 'OpenFire modules',
    'summary': 'Affichage des paiements dans les factures',
    'description': u"""
Module de lien entre impression factures et en-tête externe:

- Personnalisation des rapports de factures
    """,
    'website': 'openfire.fr',
    'depends': [
        'of_account_invoice_report',
        'of_external'
    ],
    'data': [
        'report/account_invoice_report_templates.xml',
    ],
    'installable': True,
    'auto_install': True,
}
