# -*- coding: utf-8 -*-
{
    'name' : "OpenFire / Comptabilité",
    'version' : "10.0",
    'author' : "OpenFire",
    'website' : "www.openfire.fr",
    'category' : "Generic Modules/Accounting",
    'description': """
Module de comptabilité OpenFire.
======================================

- Ajout de la rubrique 'Rapports' dans les paramètres de configuration
- Factures : afficher le boutton "Envoyer par email" dans tous les cas sauf pour les factures annulées et brouillon
""",
    'depends' : [
        'account',
        'of_base',
    ],
    'demo_xml' : [],
    'data': [
        'views/of_account_view.xml',
    ],
    'installable': True,
}
