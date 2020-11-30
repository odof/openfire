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
        'website_portal',
        'website_project_issue',
        'of_base',
        'of_account_invoice_report',
        'of_service',
        'of_planning',
        'of_parc_installe',
        'of_kit',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/templates.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
