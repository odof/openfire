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
    'data' : [
        'report/of_service_parc_installe_fiche_intervention.xml',
        'report/of_planning_rapport_intervention.xml',
        'views/of_service_parc_installe_view.xml',
        'views/of_planning_intervention_template_views.xml',
        'views/of_service_parc_installe_view_templates.xml',
        'wizard/of_wizard_invoice_to_parc_installe_view.xml'
    ],
    'qweb': [
        'static/src/xml/*.xml',
        ],
    'installable': True,
    'auto_install': True,
}
