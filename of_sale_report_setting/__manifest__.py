# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Paramétrage du rapport de vente",
    'version': '16.0.1.0.0',
    'license': 'LGPL-3',
    'author': "OpenFire",
    'website': 'https://www.openfire.fr',
    'category': 'OpenFire',
    'summary': "Options de paramétrage du rapport de vente devis/commande",
    'depends': [
        'of_sale',
    ],
    'data': [
        'security/of_sale_report_setting_security.xml',
        'security/ir.model.access.csv',
        'report/ir_actions_report_templates.xml',
        'report/report_account_move.xml',
        'views/of_sale_document_layout.xml',
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml',
        'views/sale_order_views.xml',
    ],
    'assets': {
        'web.assets_common': [
            'of_sale_report_setting/static/src/css/of_sale_report_setting_style.css',
        ],
        'web.report_assets_common': [
            'of_sale_report_setting/static/src/css/sale_report_style.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
