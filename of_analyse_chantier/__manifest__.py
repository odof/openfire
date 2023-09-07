# -*- coding: utf-8 -*-

{
    'name': u"OpenFire / Analyse de chantier",
    'version': '10.0.1.1.0',
    'author': u"OpenFire",
    'license': '',
    'category': 'OpenFire',
    'description': u"""
Analyse de chantier OpenFire
==========================


""",
    'website': 'www.openfire.fr',
    'depends': [
        'of_purchase',
        'of_sale',
        'of_account',
        'of_kit',
        'of_planning',
        'analytic'
    ],
    'data': [
        'security/of_analyse_chantier_security.xml',
        'security/ir.model.access.csv',
        'views/of_analyse_chantier_views.xml',
        'views/res_config_settings_views.xml',
        'wizards/of_analyse_chantier_wizard_views.xml',
        'hooks/hook.xml',
        ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
