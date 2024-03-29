# -*- coding: utf-8 -*-

{
    "name" : "OpenFire / Remise vente",
    "version" : "10.0.1.1.0",
    "author" : "OpenFire",
    "description" : """
Utilisation d'une formule pour la remise des lignes de commande.
La formule accepte l'operation "+", interprétée comme un cumul de remises successives (il ne s'agit donc pas d'une addition mathématique).
""",
    "website" : "www.openfire.fr",
    "depends" : ["sale"],
    "category" : "OpenFire",
    "data" : [
        'hooks/pre_hook.xml',
        'views/of_sale_discount_view.xml',
        'report/of_sale_discount_report.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
