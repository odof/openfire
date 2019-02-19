# -*- coding: utf-8 -*-

##############################################################################
#
#    OpenFire
#    Version OF10.0
#
#    Module conçu et développé par OpenFire SAS
#
##############################################################################

{
    'name' : "OpenFire / Module spécifique 1",
    'version' : "10.0.1.0.0",
    'author' : "OpenFire",
    'website' : "www.openfire.fr",
    'category': "Module OpenFire",
    'summary': u"Fonctionnalités spécifiques 1",
    'description': u"""
Module OpenFire spécifique 1
============================
Ce module ajoute des fonctionnalités demandées par une société.

 - Modification de l'affichage de la vue liste dans les devis et bons de commande
 - Export compta FEC : prend la date de création de l'écriture comptable à la place de sa date comme critère de sélection (pour export mensuel)

""",
    'depends' : [
        'sale_order_dates',
        'of_account_fec',
        'of_planning',
    ],
    'data' : [
        'views/of_zz_1_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
