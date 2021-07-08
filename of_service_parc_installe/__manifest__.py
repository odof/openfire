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
        'of_account',
    ],
    'data' : [
        'report/of_service_parc_installe_fiche_intervention.xml',
        'views/of_service_parc_installe_view.xml',
        'wizard/of_wizard_invoice_to_parc_installe_view.xml'
    ],
    'installable': True,
    'auto_install': True,
}
