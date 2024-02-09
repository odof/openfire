# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / Gestion des débours",
    'author': "OpenFire",
    'version': '10.0.1.0.0',
    'category': "Generic Modules",
    'description': u"""Module OpenFire pour la gestion des débours.
""",
    'depends': [
        'of_planning',
        'of_sale_quote_template',
    ],
    'data': [
        'views/account_move_line_views.xml',
        'views/of_outlay_analysis_entry_views.xml',
        'views/of_outlay_analysis_line_views.xml',
        'views/of_outlay_analysis_value_views.xml',
        'views/of_outlay_analysis_views.xml',
        'views/of_outlay_management_templates.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
}
