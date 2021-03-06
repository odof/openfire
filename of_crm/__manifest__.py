# -*- coding: utf-8 -*-

{
    'name': "OpenFire / CRM",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "http://openfire.fr",
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

Workflow CRM
------------

 - Mise en place d'un nouveau workflow CRM automatisé
 - Modification du workflow des devis/commandes
 - Ajout de la possibilité de plannifier des RDVs techniques depuis les opportunités
 - Refonte des activités
 - Mise en place d'un tunnel de conversion
""",
    'depends': [
        'crm',
        'sale_crm',
        'of_geolocalize',
        'of_map_view',
        'of_gesdoc',
        'of_web_widgets',
        'of_calendar',
        # 'of_base',  # <- par of_base_location
        'of_base_location',
        'of_planning',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/of_crm_security.xml',
        'wizards/of_crm_activity_action_views.xml',
        'reports/of_crm_funnel_conversion_views.xml',
        'views/crm_lead_views.xml',
        'views/sale_order_views.xml',
        'views/partner_views.xml',
        'views/of_crm_projet_views.xml',
        'views/of_planning_intervention_views.xml',
        'views/of_crm_templates.xml',
        'reports/of_crm_fiche_rdv_report_view.xml',
        'data/data.xml',
    ],
    'qweb': [
        'static/src/xml/of_sales_team_dashboard.xml',
    ],
    'installable': True,
}
