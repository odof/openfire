# -*- coding: utf-8 -*-

{
    'name': 'OpenFire External',
    'author': 'OpenFire',
    'version': '10.0',
    'category': 'OpenFire modules',
    'summary': 'Default PDF header/footer rendering',
    'description': """
Module de pied de page de rapport externe personnalisé par société. (vue external_layout_footer)
Ajoute un onglet de configuration du pied de page dans la fiche société
Il est prévu d'ajouter quelques modèles d'entêtes dans une version ultérieure
    """,
    'website': 'openfire.fr',
    'depends': ['report','of_base'],
    'data': [
        'views/of_external_layout.xml',
        'views/of_company_views.xml'
    ],
    'installable': True,
    'auto_install': False,
}
