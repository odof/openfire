# -*- coding: utf-8 -*-

{
    'name' : "OpenFire CRM",
    'version' : "10.0.1.0.0",
    'author' : "OpenFire",
    'website' : "http://openfire.fr",
    'category': 'Customer Relationship Management',
    'description': u"""
Module OpenFire pour le CRM Odoo
================================

 - Ajout du champ site web dans les pistes/opportunités.
 - Recherche du code postal par préfixe.
 - Retrait du filtre de recherche par défaut dans la vue "Mon pipeline".
""",
    'depends' : [
        'crm',
        'sale_crm',
    ],
    'data' : [
        'views/of_crm_view.xml',
    ],
    'installable': True,
}
