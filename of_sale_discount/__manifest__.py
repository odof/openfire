# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Remise vente",
    'version': '16.0.1.0.0',
    'author': "OpenFire",
    'category': 'OpenFire',
    'sequence': 15,
    'summary': "Generic Modules/Sales & Purchases",
    'website': 'https://www.openfire.fr',
    'description': "",
    'depends': [
        'sale',
    ],
    'data': [
        'security/res_groups.xml',
        'views/res_config_settings_view.xml',
        'views/product_pricelist_item_views.xml',
        'views/account_move_line_views.xml',
        'views/sale_order_line_views.xml',
        'report/sale_report.xml',
        'report/invoice_report.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
}
