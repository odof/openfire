# -*- coding: utf-8 -*-

{
    "name" : "OpenFire - Impression acomptes factures",
    "version" : "10.0.1.0.0",
    "author" : "OpenFire",
    "description" : u"""
Module d'affichage des factures d'acompte en pied de facture
============================================================

Comptabilité :
--------------
 - Affichage du montant dû de la commande sur les factures finales validées (correspond au montant TTC de la commande moins les paiements enregistrés sur toutes les factures liées à la commande)

Configuration de comptabilité :
-------------------------------
 - Ajout du choix d'impression des acomptes sur les factures (affichage des paiements des acomptes / acomptes en lignes de factures)

Rapport de comptabilité :
-------------------------
 - Modification de l'impression des lignes de facture en fonction du paramètrage (affichage des acomptes en paiement / ligne)
 - Modification des montants affichés sur la facture en fonction du paramètrage (montant de la commande / montant de la facture)
""",
    "website" : "www.openfire.fr",
    "depends" : ["of_account_invoice_report", "web"],
    "category" : "OpenFire",
    "license": "",
    "data" : [
        'views/of_sale_acompte_views.xml',
        'report/of_invoice_report_templates.xml',
    ],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
