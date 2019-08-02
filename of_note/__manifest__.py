# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenFire
#
##############################################################################

{
    'name' : "OpenFire / Module Notes",
    'version' : "1.0",
    'author' : "OpenFire",
    'website' : "www.openfire.fr",
    'category' : "OpenFire",
    'description': """
Module Notes : personnalisation du module note Odoo

 - Ajout du champ actif pour les tags et étapes
 - Ajout des utilisateurs concernés et client sur les notes
""",
    'depends' : [
        'note',
        'of_utils',
    ],
    'data' : [
        'security/of_note_security.xml',
        'views/of_note_views.xml',
    ],
    'installable': True,
}
