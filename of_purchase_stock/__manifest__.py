# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Purchase Stock",
    'version': '16.0.1.0.0',
    'license': 'LGPL-3',
    'author': "OpenFire",
    'category': 'OpenFire',
    'summary': "Module de lien entre les achats, les marges et les stocks",
    'website': 'https://www.openfire.fr',
    'depends': [
        'purchase_stock',
        'of_stock_account',  # of_stock_account > of_account > of_product_brand > of_product
    ],
    'data': [
        'views/product_views.xml',
        'reports/of_purchase_report_views.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
