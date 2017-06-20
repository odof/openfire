# -*- coding: utf-8 -*-

{
    "name" : "OpenFire Sale Appro",
    "version" : "10.0.1.0.0",
    "author" : "OpenFire",
    "description" : """
Demande d'approvisionnement lancée depuis le bon de livraison client
""",
    "website" : "www.openfire.fr",
    "depends" : ["sale"],
    "category" : "OpenFire",
    "data" : [
        'views/of_sale_appro_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
