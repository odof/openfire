# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Sale Stock",
    'version': '16.0.1.0.0',
    'author': "OpenFire",
    'category': 'OpenFire',
    'summary': "Delivery management for sale orders",
    'website': 'https://www.openfire.fr',
    'description': "",
    'depends': [
        'sale_stock',
        'of_sale_report_setting',
    ],
    'data': [
        'reports/ir_actions_report_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
