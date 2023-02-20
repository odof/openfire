# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Produits (articles)",
    'version': '10.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "Generic Modules/Sales & Purchases",
    'description': "",
    'depends': [
        'product',
        'purchase',
        'sale_stock',
        'of_utils',
    ],
    'data': [
        'security/of_product_security.xml',
        'views/product_views.xml',
        'views/product_supplierinfo_view.xml',
        'views/of_product_tag_views.xml',
        'views/product_category_views.xml',
        'views/res_config_settings_views.xml'
    ],
    'installable': True,
    'post_init_hook': 'post_init_hook',
}
