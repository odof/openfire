# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / Écritures récurrentes",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'license': '',
    'website': "www.openfire.fr",
    'category': "Generic Modules/Accounting",
    'description': u"""
Module des écritures récurrentes OpenFire.
==========================================

Permet de charger un modèle de pièce comptable de façon récurrente sur une période donnée.
- Option pour charger les écritures du premier/dernier mois au prorata des jours impactés.
- Option pour générer automatiquement une extourne au début/à la fin de la récurrence.
""",
    'depends': [
        'account_move_template',
    ],
    'demo_xml': [],
    'data': [
        'views/account_move_template.xml',
        'wizards/select_template.xml',
    ],
    'installable': True,
}
