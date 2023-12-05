# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Product standards",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': 'OpenFire',
    'summary': "Normes produits",
    'depends': [
        'of_sale',  # of_sale > of_account > of_product_brand > of_product
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/of_product_standard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
