# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenFire
#
##############################################################################

{
    'name' : "OpenFire / Module Notes",
    'version' : "10.0.1.0.0",
    'author' : "OpenFire",
    'website' : "www.openfire.fr",
    'category' : "OpenFire",
    'description': """
Module Notes : personnalisation du module note Odoo

 - Retrait de la personnalisation des étapes par utilisateur : l'étape d'une note est commune à tous.
 - Possibilité de désactiver les étiquettes et étapes
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
