# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / Contrôles d'accès",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'license': "",
    'category': "OpenFire",
    'description': u"""
Module de modification des droits
=================================

- Modification des droits Odoo standards et OpenFire
""",
    'website': "www.openfire.fr",
    'depends': [
        'of_crm',
        'of_project_issue',
        'of_followup',
        'of_service',
        'of_parc_installe',
        'of_questionnaire',
        'of_sale',
        'of_user_profile',
        'of_account_margin',
    ],
    'data': [
        'security/of_access_control_security.xml',
        'security/ir.model.access.csv',
        'views/of_parc_installe_views.xml',
        'views/of_res_config_views.xml',
        'views/project_issue_views.xml',
        'views/stock_views.xml',
        'views/sale_views.xml',
        'views/account_views.xml',
        'views/menus.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
