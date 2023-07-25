# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': u"OpenFire / Portail du site internet",
    'version': '10.0.2.2.0',
    'license': 'AGPL-3',
    'author': u"OpenFire",
    'category': u"OpenFire",
    'description': u"""
Module OpenFire pour le portail du site internet
================================================
- Ajout des contrats dans le portail (interventions récurrentes)
- Ajout de la possibilité d'uploader un fichier depuis le portail

""",
    'website': u"www.openfire.fr",
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
        'of_document_website',
        'auth_signup',
        'of_user_profile',
    ],
    'data': [
        'security/of_website_portal_security.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/of_website_portal_views.xml',
        'views/res_users_views.xml',
        'views/templates_views.xml',
        'views/res_config_views.xml',
        'wizards/portal_user_wizard_views.xml',
        'templates/website_portal_sale_views.xml',
        'data/post_update.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
