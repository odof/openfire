# -*- coding: utf-8 -*-

{
        "name": "OpenFire / Utilitaires",
        "version": "10.0.1.0.0",
        "author": "OpenFire",
        "website": "http://www.openfire.fr",
        "category": "Generic Modules",
        "description": u"""
Module OpenFire d'utilitaires.
==============================

- Ajout des Objets 'of.jours' et 'of.mois' qui contiennent les jours de la semaine et les mois de l'année.
- Ajout du type de champ odoo Biginteger.
""",
        "depends": [
            'of_base',
            'sale',
        ],
        "init_xml": [],
        "demo_xml": [],
        "data": [
            'security/ir.model.access.csv',
            'views/of_utils_templates.xml',
            'data/of_utils_data.xml',
        ],
        "installable": True,
}
