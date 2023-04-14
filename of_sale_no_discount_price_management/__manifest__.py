# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Remise interdite et gestion de prix",
    'version': '16.0.1.0.0',
    'author': "OpenFire",
    'category': 'OpenFire',
    'summary': "Link module between of_sale_no_discount and of_sale_price_management",
    'website': 'https://www.openfire.fr',
    'description': "",
    'depends': [
        'of_sale_price_management',
        'of_sale_no_discount'
    ],
    'data': [
        'views/sale_order_views.xml',
        'wizard/of_sale_price_management_views.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
    'license': 'LGPL-3',
}
