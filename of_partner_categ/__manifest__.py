# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenFire
#
##############################################################################

{
    'name' : "OpenFire / Ajout des catégories de partenaires",
    'version' : "1.1",
    'author' : "OpenFire",
    'website' : "www.openfire.fr",
    'category' : "OpenFire",
    'description': """
Module qui ajoute des catégories de partenaires (en plus des étiquettes).

Possibilité de les hiérarchiser.
""",
    'depends' : [],
    'data' : [
        'security/ir.model.access.csv',
        'of_partner_categ_view.xml',
    ],
    'installable': False,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:sorderttabstop=4:shiftwidth=4:
