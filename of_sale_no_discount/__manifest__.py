# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Remise interdite",
    'version': '16.0.1.0.0',
    'author': "OpenFire",
    'category': 'OpenFire',
    'summary': "Deactivate discount on sale orders and invoices depending on product category",
    'website': 'https://www.openfire.fr',
    'description': "",
    'depends': [
        'of_product',
        'of_sale_discount',
    ],
    'data': [
        'security/res_groups.xml',
        'views/sale_order_views.xml',
        'views/product_product_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
}
