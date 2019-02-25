# -*- coding: utf-8 -*-

{
    "name": "OpenFire Contract Planning",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    'license': 'AGPL-3',
    "description": """
Contrat OpenFire
================

- Ajout des contrats spécifiques OpenFire
- Modification des services pour fonctionner avec les contrats.
- Ajout d'élément facturable sur les services
- Ajout du choix d'un modèle d'intervention sur les services
""",
    "website": "www.openfire.fr",
    "depends": [
        "of_contract",
        "of_service_parc_installe",
        "of_account",
    ],
    "category": "OpenFire",
    "data": [
        'views/of_contract_planning_views.xml',
        'security/ir.model.access.csv',
        'security/of_contract_planning_security.xml',
        'wizards/of_contract_planning_wizard_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
