# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Sale Stock",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'category': 'OpenFire',
    'summary': "Module de lien entre les ventes, les marques et les stocks",
    'website': 'https://www.openfire.fr',
    'depends': [
        'of_sale_report_setting',  # of_sale_report_setting > of_sale > (of_account / sale_stock)
        'of_product_brand',
    ],
    'data': [
        'views/sale_order_views.xml',
        'views/product_category_views.xml',
        'reports/ir_actions_report_templates.xml',
        'reports/of_sale_report_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
