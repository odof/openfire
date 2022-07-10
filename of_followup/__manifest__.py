# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / Suivi des dossiers",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'license': "",
    'category': "OpenFire",
    'description': u"""
Outil de suivi des dossiers
===========================

Mise en place d'un workflow de suivi de l'avancé des dossiers une fois le bon de commande signé.
""",
    'website': "www.openfire.fr",
    'depends': [
        'of_document',
        'of_planning',
        'of_sale',
        'of_sale_quote_template',
        'of_sale_kanban',
        'of_service',
        'web',
        'web_widget_color',
    ],
    'data': [
        'security/of_followup_security.xml',
        'data/of_followup_data.xml',
        'security/ir.model.access.csv',
        'views/of_followup_views.xml',
        'views/menus.xml',
        'views/of_followup_settings_views.xml',
        'views/of_followup_templates.xml',
        'wizards/of_followup_confirm_next_step_views.xml',
        'wizards/of_project_followup_migration_wizard_views.xml',
    ],
    'qweb': [
        'static/src/xml/of_followup.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
