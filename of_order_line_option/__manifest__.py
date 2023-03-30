# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Order Line Option",
    'version': '16.0.1.0.0',
    'author': "OpenFire",
    'category': 'OpenFire',
    'sequence': 15,
    'summary': "Options for sale and purchase order lines",
    'website': 'https://www.openfire.fr',
    'description': "",
    'depends': [
        'purchase',
        'sale_margin',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/of_order_line_option_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
