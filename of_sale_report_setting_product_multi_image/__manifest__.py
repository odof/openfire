# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Sale Report Setting Product Multi Image",
    'version': '16.0.1.0.0',
    'license': 'LGPL-3',
    'author': "OpenFire",
    'website': 'https://www.openfire.fr',
    'category': 'OpenFire',
    'summary': "Print product images for Quotation/Order report",
    'depends': [
        'of_sale_report_setting',
        'product_multi_image',
    ],
    'data': [
        'reports/ir_actions_report_templates.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
