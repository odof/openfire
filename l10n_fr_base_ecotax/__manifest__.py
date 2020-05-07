# -*- encoding: utf-8 -*-

{
    'name': 'L10n FR Ecotax',
    'version': '10.0.1.0.0',
    'category': 'French Localization',
    'license': 'AGPL-3',
    'summary': "Ecotax for France",
    'author': "OpenFire",
    'depends': [
        'account',
        'sale',
        'of_product',
    ],
    'data': [
        'views/product_view.xml',
        'views/sale_order_report_templates.xml',
        'views/account_invoice_report_templates.xml',
    ],
    'installable': True,
}
