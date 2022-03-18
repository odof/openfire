# -*- coding: utf-8 -*-

{
    'name': "OpenFire / Base centrale des articles",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "http://www.openfire.fr",
    'category': "OpenFire",
    'description': u"""
Module OpenFire pour bases de centralisation des tarifs.
========================================================

- Ajoute un champ de notes de mise à jour dans les marques.
- Ajoute des fonctions de récupération des stocks pour le tarif centralisé, configurable par marque et par utilisateur.
- Ajoute un profil d'utilisateur "Distributeur" pour identifier facilement les distributeurs.
  Les distributeurs sont considérés comme les utilisateurs inactifs : ils ne ressortent dans aucun champ.
""",
    'depends': [
        'of_product',
        'of_product_brand',
        'of_import',
        'of_user_profile',
    ],
    'data': [
        'data/res_users_data.xml',
        'views/of_datastore_supplier_views.xml',
        'views/res_users_views.xml',
    ],
    'installable': True,
}
