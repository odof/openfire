# -*- coding: utf-8 -*-

{
    "name": u"OpenFire / Paiements ventes",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    "description": u"""
Paiements depuis les bons de commande client
============================================

- Possibilité de générer un paiement depuis la commande client.
- Le paiement sera automatiquement lié aux factures générées depuis ce bon de commande.
- Ajout d'un smart button paiements sur les commandes
- Modification de l'impression de devis/commande
""",
    "website": "www.openfire.fr",
    "depends": ["of_sale", "of_account_payment_mode"],
    "category": "OpenFire",
    "data": [
        'views/of_sale_payment_view.xml',
        'report/of_sale_payment_report_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
