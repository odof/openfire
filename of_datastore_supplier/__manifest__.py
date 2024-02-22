# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Base centrale des articles",
    'version': "16.0.1.0.0",
    'license': "AGPL-3",
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "OpenFire",
    'summary': "Centralisation des articles",
    'depends': [
        'of_product_brand',
        'of_purchase_stock',
        'of_user_profile',
        'of_sale',
    ],
    'data': [
        'data/res_users_data.xml',
        'views/of_product_brand.xml',
        'views/product_template.xml',
        'views/res_users_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
