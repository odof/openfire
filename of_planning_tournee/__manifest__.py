# -*- encoding: utf-8 -*-

{
    'name': u'OpenFire / Planning des tournées',
    'version': '10.0.2.0.0',
    'license': 'AGPL-3',
    'author': 'OpenFire',
    'website': 'http://www.openfire.fr',
    'category': 'Generic Modules/Gestion des interventions',
    'description': u"""Gestion des tournées
     - Planification RDV dans Planning Intervention
     - RDV pour les clients
     - Recherche géolocalisée des clients (Adresse Livraison)""",
    'depends': [
        'of_service',
        'of_geolocalize',
        'of_map_view',
        'of_base_location',
        'of_sale',
    ],
    'init_xml': [],
    'demo_xml': [],
    'data': [
        'security/ir.model.access.csv',
        'wizard/rdv_view.xml',
        'views/of_planning_intervention_view.xml',
        'views/of_planning_tournee_view.xml',
        'views/of_intervention_settings_views.xml',
        'views/templates.xml',
    ],
    'installable': True,
}
