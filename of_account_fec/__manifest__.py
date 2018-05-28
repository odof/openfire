# -*- coding: utf-8 -*-

{
    'name' : 'OpenFire FEC',
    'author': 'OpenFire',
    'version' : '10.0.1.0.0',
    'summary': 'extension de l10n_fr_fec',
    'description': """
OpenFire FEC\n
======================\n
- Ajout choix des journaux
- Permettre à un module qui hériterait de ce module de prendre la date de création de l'écriture comptable à la place de sa date comme critère de sélection
    """,
    'category': 'OpenFire modules - Accounting',
    'website': 'openfire.fr',
    'depends' : ['l10n_fr_fec'],
    'data': [
        'wizard/of_account_fec_view.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
