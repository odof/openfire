# -*- coding: utf-8 -*-

{
    'name': u"OpenFire / Configurateur de plan de travail en ligne",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'category': "OpenFire",
    'summary': u"Configurateur de plan de travail en ligne",
    'license': 'LGPL-3',
    'description': u"""
Module OpenFire pour la configuration de plan de travail depuis le site internet
================================================================================
""",
    'website': "www.openfire.fr",
    'depends': [
        'of_base',
        'of_product',
        'of_sale',
        'ofab_pricelist',
        'of_website_portal',
        'base_comment_template',
    ],
    'data': [
        'data/of_website_worktop_configurator_data.xml',
        'security/ir.model.access.csv',
        'reports/sale_report_templates.xml',
        'views/of_website_worktop_configurator_views.xml',
        'views/partner_views.xml',
        'views/product_views.xml',
        'views/sale_views.xml',
        'views/of_website_worktop_configurator_templates.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
