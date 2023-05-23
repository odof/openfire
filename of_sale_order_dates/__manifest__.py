{
    'name': "OpenFire / Dates on Sale Orders",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "OpenFire",
    'depends': [
        'of_sale_report_setting',
    ],
    'data': [
        'reports/sale_report_templates.xml',
        'views/res_config_settings_views.xml',
        'views/sale_order_views.xml',
    ],
}
