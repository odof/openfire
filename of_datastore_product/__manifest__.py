# -*- encoding: utf-8 -*-

{
    "name" : "OpenFire / Gestion des produits",
    "version" : "10.0.1.0.0",
    "author" : "OpenFire",
    "website" : "http://www.openfire.fr",
    "category" : "Generic Modules",
    "description": """
Module OpenFire de centralisation des tarifs.
=============================================

Divers serveurs de tarifs peuvent être configurés, chacun correspondant à une base OpenFire et à un fournisseur.
Les produits présents sur la base du fournisseur deviennent accessibles depuis la base courante.

Un produit d'une base fournisseur peut être intégré directement à un devis / une commande / une facture.
Un tel produit est affiché en couleur orange dans le formulaire de la ligne de devis/commande/facture.
A la sauvegarde du devis/commande/facture, le produit est définitivement importé sur la base courante.

Il est possible d'associer des produits existants aux produits de la base fournisseur, puis de mettre à jour simplement ces produits.
Ces fonctionnalités sont accessibles depuis la page des produits ou depuis la page de configuration du serveur du fournisseur.

Il est possible de lancer une mise à jour des produits depuis le menu de droite des produits, ou depuis la configuration de la base fournisseur.
Les produits dont le produit associé sur la base fournisseur a été désactivé/supprimé seront désactivés si il n'en reste plus en stock

Un utilitaire permet de supprimer tous les produits inutilisés, depuis le menu Ventes/Configuration/Produits

Les nomenclatures de la base fournisseur sont également disponibles pour l'intégration à un devis (sans possibilité d'import de la nomenclature)

Fonctionnalités à venir :
 - Détection de modifications sur les bases fournisseur
 - Utilisation de files d'attente pour les connexions distantes

/!\ Information OpenFire :
Ce module nécessite l'installation de erppeek sur le serveur : sudo pip install erppeek
""",
    "depends" : [
#           # Les marques sont utilisées pour filtrer les produits accédés dans la base centralisée
#         'of_product_brand',
#         # of_product définit les champs dans product_supplierinfo
#         'of_product',
#         'of_sale',
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
    ],
    "init_xml" : [ ],
    "demo_xml" : [ ],
    "data" : [
#         'security/ir.model.access.csv',
#         'wizard/of_datastore_update_product.xml',
#         'wizard/of_remove_unused_products.xml',
        'wizard/of_datastore_import_brand.xml',
        'views/of_datastore_product_view.xml',
    ],
#     'css' : [
#         "static/src/css/of_datastore_product.css",
#     ],
#     'js': [
#         'static/src/js/of_datastore_product.js'
#     ],
    "installable": True,
    'active': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
