# -*- coding: utf-8 -*-

##############################################################################
#
#    OpenFire
#
##############################################################################

{
    'name' : u"OpenFire / Module de lien entre service, interventions et parc installé",
    'version' : "10.0.1",
    'author' : "OpenFire",
    'website' : "www.openfire.fr",
    'category' : "OpenFire",
    'description': """
Module de lien entre service, interventions et parc installé
""",
    'depends' : [
        'of_parc_installe',
        'of_planning_tournee',
        'of_planning_view',
        'of_account',
    ],
    'data': [
        'security/of_service_parc_installe_security.xml',
        'data/of_service_parc_installe_data.xml',
        'report/of_service_parc_installe_fiche_intervention.xml',
        'report/of_planning_rapport_intervention.xml',
        'report/of_service_parc_installe_demande_intervention_templates.xml',
        'views/of_service_parc_installe_view.xml',
        'views/of_planning_intervention_template_views.xml',
        'views/of_service_parc_installe_view_templates.xml',
        'views/res_views.xml',
        'views/project_issue_views.xml',
        'views/config_settings_views.xml',
        'wizard/of_wizard_invoice_to_parc_installe_view.xml',
        'wizard/of_project_issue_migration_wizard_views.xml',
    ],
    'qweb': [
        'static/src/xml/*.xml',
        ],
    'installable': True,
    'auto_install': True,
}
