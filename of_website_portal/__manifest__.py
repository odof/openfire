# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / Portail du site internet",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'license': "",
    'category': "OpenFire",
    'description': u"""
Module OpenFire pour le portail du site internet
================================================
- Ajout des contrats dans le portail (interventions récurrentes)
- Ajout de la possibilité d'uploader un fichier depuis le portail

""",
    'website': "www.openfire.fr",
    'depends': [
        'base',
        'website_portal',
        'website_project_issue',
        'website_portal_sale',
        'of_base',
        'of_account_invoice_report',
        'of_service',
        'of_planning',
        'of_parc_installe',
        'of_kit',
    ],
    'data': [
        'security/of_website_portal_security.xml',
        'security/ir.model.access.csv',
        'views/of_website_portal_views.xml',
        'views/templates_views.xml',
        'templates/website_portal_sale_views.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

