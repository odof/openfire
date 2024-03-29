# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Contrat Custom",
    'version': '10.0.2.1.1',
    'author': "OpenFire",
    'license': 'AGPL-3',
    'summary': u"Ajout des contrats OpenFire",
    'description': u"""
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
 - Valeur d'indexation

""",
    'website': "www.openfire.fr",
    'depends': [
        'of_service_parc_installe',
        'of_account',
        'of_account_tax',
        'of_planning_tournee',
        'of_project_issue',
        'of_base',
        'of_analytique',
        'of_service_purchase',
        'of_sale_type',
    ],
    'category': 'OpenFire',
    'data': [
        'security/of_contract_custom_security.xml',
        'reports/of_contract_invoice_report_templates.xml',
        'reports/of_contract_custom_demande_intervention_templates.xml',
        'data/of_contract_custom_data.xml',
        'security/ir.model.access.csv',
        'wizards/of_contract_invoicing_wizard_views.xml',
        'views/account_views.xml',
        'views/of_better_zip_views.xml',
        'views/of_contract_custom_views.xml',
        'views/of_planning_views.xml',
        'views/of_service_views.xml',
        'views/res_partner_views.xml',
        'views/config_settings_views.xml',
        'views/hr_employee_views.xml',
        'reports/of_contract_custom_templates.xml',
        'wizards/of_contract_avenant_wizard_views.xml',
        'wizards/of_contract_indice_wizard_views.xml',
        'wizards/of_contract_line_cancel_wizard_views.xml',
        'wizards/of_contract_mass_avenant_wizard_views.xml',
        'wizards/of_contract_revision_wizard_views.xml',
        'hooks/post_hooks.xml',
        ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
