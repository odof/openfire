# -*- coding: utf-8 -*-

{
    "name" : "OpenFire Sale Discount",
    "version" : "10.0.1.0.0",
    "author" : "OpenFire",
    "description" : """
Utilisation d'une formule pour la remise des lignes de commande.
La formule accepte l'operation "+", interprétée comme un cumul de remises successives (il ne s'agit donc pas d'une addition mathématique).
""",
    "website" : "www.openfire.fr",
    "depends" : ["sale"],
    "category" : "OpenFire",
    "data" : [
        'views/of_sale_discount_view.xml',
        'report/of_sale_discount_report.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
