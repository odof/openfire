# -*- coding: utf-8 -*-

{
    'name': 'OpenFire multi logos',
    'author': 'OpenFire',
    'version': '10.0',
    'category': 'OpenFire modules',
    'summary': 'Multi logos',
    'description': """
        Permet aux sociétés d'avoir plusieurs logos en tant que logos secondaires.
        Ces logos sont affichés dans l'onglet "Logos" de la fiche société et dans les entêtes des rapports externes.

        Allow a company to have several logos as secondary logos.
        These logos are displayed in a tab named "Logos" in the company form and in external report headers.
    """,
    'website': 'openfire.fr',
    'depends': [
        'of_base',
        'of_external',
        ],
    'data': [
        'views/of_company_multi_logos_views.xml',
        'security/ir.model.access.csv',
        'report/of_multi_logos_report_templates.xml',
    ],
    'installable': True,
    'auto_install': False,
}
