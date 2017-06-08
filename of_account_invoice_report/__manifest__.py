# -*- coding: utf-8 -*-

{
    'name': 'OpenFire - Impression Factures',
    'author':'OpenFire',
    'version': '10.0',
    'category': 'OpenFire modules',
    'summary': 'Affichage des acomptes dans les factures',
    'description': """
Module de factures :
- Personnalisation des rapports de factures
- Ajout des paiements dans les rapports de factures
    """,
    'website': 'openfire.fr',
    'depends': [
        'account',
    ],
    'data': [
        'report/of_invoice_report_templates.xml',
    ],
    'installable': True,
    'auto_install': False,
}
