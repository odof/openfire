# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenFire
#
##############################################################################

{
    'name': u"OpenFire / Module Parc installé - Cheministe",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "OpenFire",
    'description': u"""
Module Parc installé : spécial cheministe.
""",
    'depends': [
        'of_parc_installe',
        'of_service_parc_installe',
    ],
    'data': [
        'views/of_parc_cheministe_view.xml',
        'views/of_planning_intervention_template_views.xml',
        'reports/of_parc_chem_fiche_intervention.xml',
        'reports/of_parc_chem_rapport_intervention.xml',
    ],
    'installable': True,
}
