# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Sale Payment Schedule",
    'version': '16.0.1.0.0',
    'author': "OpenFire",
    'category': 'OpenFire',
    'sequence': 15,
    'summary': "Payment schedule for sale orders",
    'website': 'https://www.openfire.fr',
    'description': "",
    'depends': [
        'sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/of_sale_payment_schedule_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
