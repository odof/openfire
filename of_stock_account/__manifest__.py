# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Stock Account",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "OpenFire",
    'summary': "Module de lien entre les stocks, les produits, les marques et la comptabilité",
    'depends': [
        'stock_account',
        'of_account',  # of_account > of_product_brand > of_product
    ],
    'data': [
        'views/product_category_views.xml',
        'views/product_views.xml',
        'reports/of_account_report_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
