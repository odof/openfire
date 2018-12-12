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
 - changement méthode de calcul du nombre de ventes client -> ne prend plus en compte que les ventes confirmées (et non les devis)
 - Ajout notion de 'client confirmé': un client confirmé est un client qui a au moins une vente confirmée ou une facture validée. Les autres sont des prospects.
 - Ajout fiche de projet dynamique

Fiche de projet dynamique
-------------------------

 - Dans l'onglet 'projet' d'une opportunité.
 - Configuration via le menu 'Projets' dans Ventes -> Configuration.
 - Modèles de Projets: contiennent une liste d'attributs qui seront reportés dans une fiche projet sur sélection d'un modèle.
 - Valeurs d'attributs: valeurs possible pour les attributs de type 'Choix Unique'
 - Attributs de Projets: correspond à un 'champ' d'une fiche projet. possède un libellé et un type.
    Les types possibles sont pour l'instant 'Texte Court', 'Booléen', 'Date' et 'Choix Unique'.
    Dans une future version les types 'Monétaire' et 'Choix Multiples' pourront être implémentés.
""",
    'depends' : [
        'crm',
        'sale_crm',
        'of_geolocalize',
        'of_map_view',
        'of_gesdoc',
        'of_web_widgets',
        'of_calendar',
        'of_base',
    ],
    'data' : [
        'views/of_crm_view.xml',
        'views/of_crm_projet_view.xml',
        'views/of_crm_templates.xml',
        'report/of_crm_fiche_rdv_report_view.xml',
        'data/data.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
}
