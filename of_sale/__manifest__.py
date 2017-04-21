# -*- coding: utf-8 -*-

{
    "name" : "OpenFire Sale",
    "version" : "10.0",
    "author" : "OpenFire",
    "description" : """
Personnalisation des ventes OpenFire

Modification de l'affichage du formulaire de devis/commande client
""",
    "website" : "www.openfire.fr",
    "depends" : ["sale"],
    "category" : "OpenFire",
    "data" : [
        'views/of_sale_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
