# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Gestion prix",
    'version': '16.0.1.0.0',
    'author': "OpenFire",
    'category': 'OpenFire',
    'sequence': 15,
    'summary': "Price management for sales orders",
    'website': 'https://www.openfire.fr',
    'description': "",
    'depends': [
        'of_sale_margin',
        'of_product_brand',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'wizards/of_sale_price_management_views.xml',
        'report/of_sale_price_management_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
