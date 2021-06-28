# -*- coding: utf-8 -*-
{
    'name': "OpenFire / Rapports comptables OCA",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'license': '',
    'website': "www.openfire.fr",
    'category': "Generic Modules/Accounting",
    'description': u"""
Module OpenFire de personnalisation des rapports comptables OCA.
================================================================

- Augmentation de la police.
- Utilisation du format paysage pour le grand livre et la balance âgée des tiers.
- Correction des montants affichés pour la balance âgée des tiers (montants proches de zéro nécessitaient un arrondi).

""",
    'depends': [
        'account_financial_report_qweb',
    ],
    'demo_xml': [],
    'data': [
        "report/reports.xml",
        "report/templates/layouts.xml",
        "report/templates/trial_balance.xml",
    ],
    'installable': True,
}
