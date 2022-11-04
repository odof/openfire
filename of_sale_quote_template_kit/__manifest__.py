# -*- coding: utf-8 -*-

{
    'name': u"OpenFire / Modèle de devis avec kit",
    'version': '10.0.1.0.0',
    'author': u"OpenFire",
    'license': '',
    'category': u"OpenFire",
    'description': u"""
Modèle de devis OpenFire
========================
Ce module modifie les modèles de devis OpenFire pour fonctionner avec les kits.


Fonctionnalités
----------------
 - Ajout de champs dans les lignes de modèles pour fonctionner avec les kits
""",
    'website': 'www.openfire.fr',
    'depends': [
        'of_sale_quote_template',
        'of_kit',
    ],
    'data': [
        'views/of_sale_quote_template_views_kit.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
