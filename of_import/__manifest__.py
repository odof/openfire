# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": u"OpenFire / OpenImport",
    "version": '10.0.1.0.0',
    "license": 'AGPL-3',
    "author": u"OpenFire",
    "website": u"openfire.fr",
    "category": u"'Extra Tools'",
    "description": u"""
Module d'import OpenFire
========================

Import général
--------------
Ce module offre un outil d'import plus efficace que l'import standard d'Odoo dans certains domaines.
Il permet en effet de mettre à jour des éléments déjà existants et garde en mémoire l'historique des imports effectués.
Le type d'éléments pouvant être importés avec ce module est limité, la détection des doublons se fait sur un champ prédéterminé sur les modèles disponibles :
 - articles : référence
 - partenaires : référence
 - pistes/opportunités : référence (nécessite l'intallation du module of_crm)
 - comptes en banques partenaire : numéro de compte
 - services OpenFire : identifiant (nécessite l'installation du module of_service)


Import de tarifs
----------------
Lors de l'import d'articles, le champ "Préfixe", si renseigné, doit correspondre au préfixe renseigné dans une marque.
Dans ce cas, la marque en question sera associée par défaut aux articles importés.
Si le préfixe n'est pas renseigné, la présence d'une colonne pour la marque (brand_id) devient obligatoire dans le fichier.
La gestion des marques se fait dans le menu Ventes/Configuration/Articles/Marques

Ce module ajoute dans les marques des champs permettant de configurer les imports de tarifs.
Ces champs permettent de modifier certaines valeurs du fichier d'import pour mieux correspondre à la base actuelle.
Les champs pouvant ainsi être personnalisés sont
 - La catégorie de l'article
 - La remise accordée par le fournisseur
 - Le prix de vente à appliquer (en fonction du prix public hors taxe)
 - Le coût total de l'article
Ces différentes valeurs peuvent être configurées par marque et par catégorie d'article ou forcées par article.

La configuration d'une formule pour la remise n'est pas obligatoire. Si elle n'est pas renseignée, le fichier d'import devra
contenir une colonne renseignant soit le prix d'achat ('of_seller_price'), soit la remise accordée par le fournisseur ('of_seller_remise')


Import de pièces jointes/images
-------------------------------
L'import de pièces jointes ou images (sur champ dédié d'un objet) nécessite que les fichiers aient été préalablement téléchargés sur le serveur.
Le fichier d'import est constitué de 5 champs :
 - name : Le nom de la pièce jointe.
 - store_fname : Le chemin complet du fichier sur le serveur (e.g. "/home/odoo/fichiers_import_55/image_27.png").
 - res_model : Le nom technique de l'objet concerné (par exemple pour les articles : "product.template").
 - res_id : Le nom permettant d'identifier l'élément auquel associer la PJ (par exemple pour un article il s'agit de la référence).
 - res_field : Pour une PJ, laisser vide. Pour une image, mettre le nom du champ concerné (pour l'image d'un article, le champ est "image").
""",
    "depends": [
        'of_product_brand',
    ],
    "demo_xml": [],
    'data': [
        'security/ir.model.access.csv',
        'wizards/of_import_update_product_brand_products.xml',
        'views/of_import_view.xml',
        'views/templates.xml',
    ],
    "installable": True,
}
