# -*- coding: utf-8 -*-

{
    'name' : 'OpenFire / Payment modes',
    'version' : '10.0.1.0.0',
    'summary': 'Use distinct payment modes within journals',
    'description': """
OpenFire Payment modes
======================
    - Ajout des catégories de paiement (étiquettes) dans les paramètres de paiement.
    - Ajout dans modes de paiement des paramètres d'affichage configurables pour la facture imprimée.

    """,
    'category': 'Accounting',
    'depends' : [
        'account',
        'of_account_invoice_report',
    ],
    'data': [
        'views/of_account_payment_mode_view.xml',
        'report/of_invoice_report_templates_extended.xml',
        'security/ir.model.access.csv',
        'security/of_account_payment_mode_security.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
