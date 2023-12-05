# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Option de ligne de commande",
    'version': '16.0.1.0.0',
    'license': 'LGPL-3',
    'author': "OpenFire",
    'category': 'OpenFire',
    'sequence': 15,
    'summary': "Gestion des options de ligne de commande pour les ventes et les achats",
    'website': 'https://www.openfire.fr',
    'depends': [
        'stock_dropshipping',
        'of_sale_margin',
        'of_sale_stock',  # easier tests management if of_order_line_option depends on of_sale_stock
        'of_purchase_stock',  # of_purchase_stock > of_stock_account > of_account
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
