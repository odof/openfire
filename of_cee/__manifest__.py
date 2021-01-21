# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / Fonction CEE",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "OpenFire",
    'description': u"""
Module Fonction CEE OpenFire
============================

Ce module permet la facturation de CEE aux fournisseurs des CEE.
""",
    'depends': [
        'of_sale',
    ],
    'data': [
        'views/account_views.xml',
        'views/sale_views.xml',
        'views/partner_views.xml',
        'wizards/of_create_cee_invoices_views.xml',
        'reports/account_report_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
