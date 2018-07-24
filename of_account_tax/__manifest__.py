# -*- coding: utf-8 -*-
{
    'name': 'OpenFire Taxes',
    'version': '10.0.1.0.0',
    'category': 'Accounting',
    'summary': 'OpenFire Taxes',
    'description': """
Gestion des taxes OpenFire
==========================

Le système de taxes OpenFire ajoute une taxe par défaut dans les positions fiscales, qui intervient lorsqu'aucune taxe n'est définie dans le produit ni dans sa catégorie de produit.

Une table de correspondance de comptes comptables est également ajoutée au niveau des taxes et est utilisée au niveau des lignes de factures.
""",
    'depends': ['account', 'sale', 'purchase'],
    'data': [
        'views/of_account_tax_view.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
}
# -*- coding: utf-8 -*-
