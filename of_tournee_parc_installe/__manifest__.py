# -*- coding: utf-8 -*-

##############################################################################
#
#    OpenFire
#
##############################################################################

{
    'name' : u"OpenFire / Module de lien entre tournée et parc installé",
    'version' : "10.0.1",
    'author' : "OpenFire",
    'website' : "www.openfire.fr",
    'category' : "OpenFire",
    'description': """
Ajout du bouton "planifier une intervention" dans les SAV et parc installé.
""",
    'depends' : [
        'of_service_parc_installe',
        'of_planning_tournee',
    ],
    'data' : [
        'views/of_tournee_parc_installe_views.xml',
        'wizard/rdv_views.xml',
    ],
    'installable': True,
    'auto_install': True,
}
