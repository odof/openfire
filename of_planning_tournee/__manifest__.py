# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': u'OpenFire / Planning des tournées',
    'version': '10.0.4.0.0',
    'license': 'AGPL-3',
    'author': 'OpenFire',
    'website': 'http://www.openfire.fr',
    'category': 'Generic Modules/Gestion des interventions',
    'description': u"""Gestion des tournées
     - Planification RDV dans Planning Intervention
     - RDV pour les clients
     - Recherche géolocalisée des clients (Adresse Livraison)
     - Optimisation d'itinéraire de tournées via OSRM
     - Réagencement manuel de la tournée
     - Affichage des itinéraires sur la planification de DI et les tournées
""",
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
        'data/ir_cron.xml',
        'security/ir.model.access.csv',
        'security/of_planning_tournee_security.xml',
        # /!\ Le fichier wizard/rdv_view.xml doit être chargé avant views/of_service_parc_views.xml
        'wizard/rdv_view.xml',
        'views/of_planning_intervention_view.xml',
        'views/of_planning_tournee_view.xml',
        'views/of_service_parc_views.xml',
        'views/of_intervention_settings_views.xml',
        'views/of_tournee_rdv_template_views.xml',
        'views/templates.xml',
        'wizard/tour_planning_optimization_view.xml',
        'wizard/tour_planning_reorganization_view.xml',
        'wizard/tour_planning_mass_sector_assignation_view.xml',
        'wizard/tour_planning_mass_route_update_view.xml',
    ],
    'installable': True,
}
