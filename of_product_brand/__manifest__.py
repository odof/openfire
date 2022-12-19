# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Products brands",
    'version': '16.0.1.0.0',
    'author': "OpenFire",
    'category': 'OpenFire',
    'sequence': 15,
    'summary': "Base module for OpenFire",
    'website': 'https://www.openfire.fr',
    'description': "",
    'depends': [
        'sale',
        'of_product'
    ],
    'data': [
        'data/of_product_brand_data.xml',
        'security/ir.model.access.csv',
        'views/of_product_brand_view.xml',
        'views/product_supplierinfo_view.xml',
        'views/product_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'wizards/of_product_brand_add_products.xml',
        'report/of_sale_report_view.xml',
        'report/of_purchase_report_views.xml',
        'report/of_account_report_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
