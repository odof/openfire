# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': u"OpenFire / État de stock de combustible pour les clients",
    'version': '10.0.1.0.0',
    'license': 'AGPL-3',
    'author': u"OpenFire",
    'category': u"OpenFire",
    'description': u"""
Module d'état de stock de combustible pour les clients
======================================================

""",
    'website': u"www.openfire.fr",
    'depends': [
        'of_base',
        'of_external',
        'of_sale_quote_template_kit',
        'stock',
        'product',
    ],
    'data': [
        'reports/external_report_templates.xml',
        'reports/stock_report_templates.xml',
        'security/ir.model.access.csv',
        'views/of_partner_fuel_stock_views.xml',
        'views/sale_quote_template_view.xml',
        'views/product_views.xml',
        'views/sale_views.xml',
        'views/stock_views.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
