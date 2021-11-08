# -*- coding: utf-8 -*-

##############################################################################
#
#    OpenFire
#    Version OF10.0
#
#    Module conçu et développé par OpenFire SAS
#
#    Compatible avec Odoo 10 Community Edition
#
##############################################################################

{
    'name' : u"OpenFire / Ventes - impression spécifique",
    'version' : "10.0.1.0.0",
    'license': '',
    'author' : "OpenFire",
    'website' : "www.openfire.fr",
    'category': "Module OpenFlam",
    'summary': u"Personnalisation des ventes OpenFire",
    'description': u"""

Module OpenFire / Ventes - impression spécifique
================================================

Module faisant le lien entre of_sale et of_external

Ajout d'un nouveau rapport 'Impression spécifique' reprenant le nom et la date choisi dans l'encart du mếme nom sur le
devis/bon de commande.
 - Surcharge de l'en-tête pour afficher un nom et une date spécifique
 
""",
    'depends' : [
        "of_sale",
        "of_external",
    ],
    'data' : [
        'views/sale_order_views.xml',
        'report/of_sale_external_reports.xml',
        'report/sale_order_reports.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
