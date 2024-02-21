# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Lab'",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "http://www.openfire.fr",
    'category': "OpenFire",
    'description': u"""
Module OpenFire pour le Lab'
============================

- Permet la création d'utilisateur interne depuis le portail avec employé associé
- Présentation application mobile
- Démo TC
- Démo optimisation de tournées
- Démo prise de RDV en ligne
- Démo signature électronique
- Démo déperdition de chaleur
- Démo dashboard métier
""",
    'depends': [
        'of_mobile',
        'of_datastore_product',
        'of_planning_tournee',
        'of_website_planning_booking',
        'yousign_sale',
        'of_calculation_heat_loss',
        'ks_dashboard_ninja',
        'partner_firstname',
    ],
    'data': [
        'data/data.xml',
        'security/of_lab_security.xml',
        'views/of_datastore_brand_views.xml',
        'views/tour_planning_optimization_views.xml',
        'views/templates.xml',
        'wizards/yousign_direct_signature_wizard_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
