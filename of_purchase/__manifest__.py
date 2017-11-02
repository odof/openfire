# -*- coding: utf-8 -*-
{
    'name': 'OpenFire Purchase',
    'version': '10.0.1.0.0',
    'category': 'Purchases',
    'summary': 'OpenFire Purchases',
    'description': """
Modifications OpenFire pour les commandes fournisseur
=====================================================

- Ajout de la date souhaitée de livraison (champ texte) pour les commandes client et fournisseur
- Ajout du client final dans les commandes fournisseur, auto-alimenté depuis la commande client
- Modification des documents imprimés pour l'ajout de ces informations
- Ajout de l'impression de la commande fournisseur sans prix
- Ajout option pour afficher la description telle que saisie dans le devis dans la commande fournisseur et les documents imprimables associés
""",
    'depends': ['purchase', 'sale'],
    'data': [
        'report/purchase_report_templates.xml',
        'report/purchase_reports.xml',
        'views/of_purchase_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
