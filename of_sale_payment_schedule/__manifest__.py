# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Echéancier de paiement des ventes",
    'version': '16.0.1.0.0',
    'license': 'LGPL-3',
    'author': "OpenFire",
    'website': 'https://www.openfire.fr',
    'category': 'OpenFire',
    'summary': "Echéancier de paiement des ventes",
    'description': "",
    'depends': [
        'of_sale_report_setting',
    ],
    'data': [
        'data/of_sale_payment_schedule_data.xml',
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/of_sale_payment_schedule_views.xml',
        'views/res_config_settings_views.xml',
        'reports/ir_actions_report_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
