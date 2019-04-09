# -*- coding: utf-8 -*-

{
    'name': 'OpenFire / Impression factures',
    'author': 'OpenFire',
    'version': '10.0.1.0.0',
    'category': 'OpenFire modules',
    'summary': 'Affichage des paiements dans les factures',
    'description': """
Module de factures :

- Personnalisation des rapports de factures

- Ajout des paiements dans les rapports de factures
    """,
    'website': 'openfire.fr',
    'depends': [
        'of_account',
    ],
    'data': [
        'data/of_account_invoice_report_data.xml',
        'report/of_invoice_report_templates.xml',
        'views/of_account_invoice_report_views.xml',
        'security/ir.model.access.csv'
    ],
    'installable': True,
    'auto_install': False,
}
