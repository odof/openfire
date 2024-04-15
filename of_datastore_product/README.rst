====================
OF Datastore Product
====================

Module OpenFire de centralisation des produits.

Fonctionnalités
###############


* Ajout d'un outil de connexion vers une base fournisseur distante, utilisable exclusivement par le compte administrateur.
* Chaque marque peut être associée à une de ces connexions.
* Elle peut alors être alimentée par les articles de la base ciblée.


* Un produit d'une base fournisseur peut être intégré directement à un devis / une commande / une facture.
* Un tel produit est affiché en couleur "rouge orangé" dans le formulaire de la ligne de devis / commande / facture.
* À la sauvegarde du devis / commande / facture, le produit est définitivement importé sur la base courante.
* Cette fonctionnalité requiert de cibler la marque voulue avec le code m:xxx, où xxx est la marque, dans l'emplacement de sélection de l'article.


* Un filtre de recherche est ajouté à la liste des articles, permettant de rechercher directement sur une base fournisseur.
* Un produit peut aussi être importé directement depuis la liste des articles, grâce à un filtre de recherche
* Cette fonctionnalité requiert d'avoir sélectionné une ou plusieurs marques référençant la même base fournisseur dans les filtres de recherche.

* Les articles déjà importés peuvent être mis à jour via une action disponible depuis la marque ou depuis a liste des articles.
* La mise à jour a aussi pour effet d'actualiser les liens des articles avec les bases distantes (meilleur effet avec la mise à jour depuis la marque)

* Une action permet de supprimer tous les produits inutilisés d'une marque.

* Un accès à la base de gestion (définie via le module of_base) permet de récupérer une liste de toutes les marques disponibles.
* Les utilisateurs peuvent demander une connexion ou déconnexion à ces marques, avec l'impact que cela aura sur leur contrat OpenFire.
