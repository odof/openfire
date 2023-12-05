# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Marques de produits",
    'version': '16.0.1.0.0',
    'license': 'LGPL-3',
    'author': "OpenFire",
    'category': 'OpenFire',
    'sequence': 15,
    'summary': "Module de gestion des marques de produits",
    'website': 'https://www.openfire.fr',
    'depends': [
        'of_product',
    ],
    'data': [
        'data/of_product_brand_data.xml',
        'security/ir_rules.xml',
        'security/ir.model.access.csv',
        'views/of_product_brand_view.xml',
        'views/product_supplierinfo_view.xml',
        'views/product_views.xml',
        'views/res_partner_views.xml',
        'views/res_users_views.xml',
        'wizards/of_product_brand_add_products.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
