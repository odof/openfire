# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Option de ligne de commande",
    'version': '16.0.1.0.0',
    'license': 'LGPL-3',
    'author': "OpenFire",
    'category': 'OpenFire',
    'sequence': 15,
    'summary': "Options for sale and purchase order lines",
    'website': 'https://www.openfire.fr',
    'description': "",
    'depends': [
        'purchase',
        'of_sale_margin',
        'sale_purchase',
        'stock_dropshipping'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_line_options_views.xml',
        'views/purchase_order_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
