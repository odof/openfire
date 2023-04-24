# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Dates sur les commandes de vente",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "OpenFire",
    'summary': "Dates sur les commandes de vente",
    'description': "",
    'depends': [
        'of_sale_report_setting',
    ],
    'data': [
        'data/ir_config_parameter.xml',
        'views/res_config_settings_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
        'reports/sale_report_templates.xml',
        'reports/account_move_report_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
