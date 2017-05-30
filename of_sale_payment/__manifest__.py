# -*- coding: utf-8 -*-

{
    "name" : "OpenFire Sale Payments",
    "version" : "10.0",
    "author" : "OpenFire",
    "description" : """
Paiements depuis les bons de commande client

Possibilité de générer un paiement depuis la commande client.
Le paiement sera automatiquement lié aux factures générées depuis ce bon de commande.
""",
    "website" : "www.openfire.fr",
    "depends" : ["sale"],
    "category" : "OpenFire",
    "data" : [
        'views/of_sale_payment_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
