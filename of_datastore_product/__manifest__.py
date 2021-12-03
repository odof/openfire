# -*- coding: utf-8 -*-

{
    'name': u"OpenFire / Tarifs centralisés",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "http://www.openfire.fr",
    'category': "Openfire",
    'description': u"""
Module OpenFire de centralisation des tarifs.
=============================================

Ajout d'un outil de connexion vers une base fournisseur distante, utilisable exclusivement par le compte administrateur.
Chaque marque peut être associée à une de ces connexions.
Elle peut alors être alimentée par les articles de la base ciblée.

Un produit d'une base fournisseur peut être intégré directement à un devis / une commande / une facture.
Un tel produit est affiché en couleur "rouge orangé" dans le formulaire de la ligne de devis / commande / facture.
À la sauvegarde du devis / commande / facture, le produit est définitivement importé sur la base courante.
Cette fonctionnalité requiert de cibler la marque voulue avec le code m:xxx, où xxx est la marque, dans l'emplacement de sélection de l'article.

Un filtre de recherche est ajouté à la liste des articles, permettant de rechercher directement sur une base fournisseur.
Un produit peut aussi être importé directement depuis la liste des articles, grâce à un filtre de recherche
Cette fonctionnalité requiert d'avoir sélectionné une ou plusieurs marques référençant la même base fournisseur dans les filtres de recherche.

Les articles déjà importés peuvent être mis à jour via une action disponible depuis la marque ou depuis a liste des articles.
La mise à jour a aussi pour effet d'actualiser les liens des articles avec les bases distantes (meilleur effet avec la mise à jour depuis la marque)

Une action permet de supprimer tous les produits inutilisés d'une marque.

/!\\\\ Information OpenFire :
Ce module nécessite l'installation de openerplib sur le serveur : sudo easy_install openerp-client-lib
""",
    'depends': [
        'of_datastore_connector',
        # Surcharge de la vue formulaire produit
        'of_product',
        # Les marques sont utilisées pour filtrer les produits accédés dans la base centralisée
        'of_product_brand',
        # Surcharge des lignes de facture
        'account',
        # Surcharge des lignes d'inventaire
        'stock',
        # Surcharge des lignes de commande fournisseur
        'purchase',
        # Utilisation du système de paramétrage d'import
        # (matching des catégories d'articles, calcul des prix d'achat et de vente, etc.)
        'of_import',
        'of_kit',
        'of_utils',
    ],
    'data': [
        'wizard/of_datastore_import_brand.xml',
        'wizard/of_datastore_update_product.xml',
        'wizard/of_remove_unused_products.xml',
        'views/of_datastore_product_view.xml',
    ],
    'qweb': [
        'static/src/xml/of_datastore_product.xml',
    ],
    'installable': True,
}
