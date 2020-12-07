# -*- coding: utf-8 -*-

{
    "name": "OpenFire / Contrat Custom",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    'license': 'AGPL-3',
    'summary': u"Ajout des contrats OpenFire",
    "description": u"""
Contrats OpenFire
=================
Création de nouveaux modèles:
 - Contrat
 - Ligne de contrat
 - Indice
 - Ligne d'indice
 
Contrats :
----------

Contrat:
 - Client payeur
 - Valeurs par défaut de facturation des lignes de contrats
 - Renouvellement automatique des contrats
 - Utilisation des indices

Ligne de contrat :
 - Prestataire qui sera en charge des différentes interventions.
 - Adresse à laquelle les interventions seront réalisés
 - Nombres d'interventions par période ainsi que mois de références
 - Articles à facturer et fréquence de facturation
 
Indices :
---------

Indice :
 - Formule d'indexation d'origine
 - Catégories liées à l'indice
 
Ligne d'indice :
 - Date de début et date de fin d'application
 - Veleur d'indexation




""",
    "website": "www.openfire.fr",
    "depends": [
        "of_contract",
        "of_service_parc_installe",
        "of_account",
        "of_service_contrat",
        "of_planning_tournee",
        "of_project_issue",
        # "date_range",
        "of_base",
    ],
    "category": "OpenFire",
    "data": [
        'data/of_contract_custom_data.xml',
        'views/of_contract_custom_views.xml',
        'views/of_parc_installe_views.xml',
        'views/of_planning_views.xml',
        'views/of_service_views.xml',
        'views/project_issue_views.xml',
        'views/res_partner_views.xml',
        'security/ir.model.access.csv',
        'security/of_contract_custom_security.xml',
        'wizards/of_contract_avenant_wizard_views.xml',
        'wizards/of_contract_custom_wizard_view.xml',
        'wizards/of_contract_indice_wizard_views.xml',
        'wizards/of_contract_line_cancel_wizard_views.xml',
        'wizards/of_contract_revision_wizard_views.xml',
        ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
