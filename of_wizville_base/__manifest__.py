# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / module spécifique Wizville",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'license': "",
    'category': "OpenFire",
    'description': u"""
Implémentation de l'api Wizville
================================
ssh-keyscan -t rsa sftp.wizville.fr >> ~/.ssh/known_hosts

""",
    'website': "www.openfire.fr",
    'depends': [
        'of_sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/of_sanitize_query.xml',
        'data/of_wizville_data.xml',
        'views/of_connector_config_settings_views.xml',
        'views/res_company_views.xml',
        'views/res_partner_views.xml',
        'views/product_template_views.xml',
        'views/of_wizville_history_views.xml',
        ],
    'qweb': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
