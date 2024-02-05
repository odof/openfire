# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / Gestion des débours",
    'author': "OpenFire",
    'version': '10.0.1.0.0',
    'category': "Generic Modules",
    'description': u"""
Module OpenFire pour la gestion des débours.
============================================

- Ajout d'un outil d'analyse des débours (Ventes / Rapports / Analyse des débours).
  Cet outil permet de suivre l'évolution d'un projet en terme de dépenses et de revenus.
- Ajout de sections analytiques qui ajoutent une précision en plus des comptes analytiques.
""",
    'depends': [
        'of_planning',
        # Le module of_purchase report retire le mode d'édition en ligne des lignes de commandes fournisseur et factures
        'of_purchase_report',
        'of_sale_quote_template',
    ],
    'data': [
        'views/account_invoice_line_views.xml',
        'views/account_invoice_views.xml',
        'views/account_move_line_views.xml',
        'views/of_account_analytic_section_views.xml',
        'views/of_outlay_analysis_entry_views.xml',
        'views/of_outlay_analysis_line_views.xml',
        'views/of_outlay_analysis_value_views.xml',
        'views/of_outlay_analysis_views.xml',
        'views/of_outlay_management_templates.xml',
        'views/purchase_order_views.xml',
        'views/sale_order_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
}
