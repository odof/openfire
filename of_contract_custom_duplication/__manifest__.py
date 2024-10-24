# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Duplication de contrats",
    'version': '10.0.1.0.0',
    'category': 'OpenFire',
    'author': "OpenFire",
    'license': 'AGPL-3',
    'summary': u"Duplication de contrats OpenFire",
    'description': u"""
Duplication de contrats OpenFire
================================
 - Affichage d'un récapitulatif des lignes à dupliquer.
 - Duplication de l'intégralité du contrat sans les lignes annulées.
""",
    'website': "www.openfire.fr",
    'depends': [
        'of_contract_custom',
    ],
    'data': [
        #'security/ir.model.access.csv',
        'wizards/of_contract_duplication_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
