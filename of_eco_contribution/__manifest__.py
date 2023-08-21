# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': u"OpenFire / Éco contribution",
    'version': '10.0.1.0.0',
    'license': 'AGPL-3',
    'author': u"OpenFire",
    'category': u"OpenFire",
    'description': u"""
Gestion des Éco contributions
=============================
""",
    'website': u"www.openfire.fr",
    'depends': [
        'of_conditionnement',
        'of_sale_quote_template_kit',
    ],
    'data': [
        'security/of_sale_stock_security.xml',
        'security/ir.model.access.csv',
        'views/account_config_settings_views.xml',
        'views/of_eco_contribution_views.xml',
        'views/product_views.xml',
        'views/sale_order_views.xml',
        'views/account_invoice_views.xml',
        'report/of_eco_contribution_templates.xml',
        'report/account_invoice_report_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
