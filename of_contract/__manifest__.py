# -*- coding: utf-8 -*-

{
    "name": "OpenFire Contract",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    'license': 'AGPL-3',
    "description": """
Extension OpenFire du module contract de l'OCA
==============================================

- Possibilité de générer manuellement les factures de plusieurs contrats sélectionnés
- Affichage des totaux HT et TTC dans la vue liste des contrats
- Possibilité de sélectionner une position fiscale au niveau du contrat, impactant la facture finale
""",
    "website": "www.openfire.fr",
    "depends": [
        "contract",
    ],
    "category": "OpenFire",
    "data": [
        'views/of_contract_views.xml',
        'wizards/of_contract_invoice_confirm.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
