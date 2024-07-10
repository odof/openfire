=================
OF Stock Account
=================

Module de lien entre les stocks, les produits, les marques et la comptabilité

Fonctionnalités
################

Ligne de factures
-----------------

* Ajout de la marque dans les lignes de factures

* Modification du calcul du champ "Nom" des lignes de factures pour afficher la marque et/ou la description en fonction des paramètres de la marque

Catégorie de produits
---------------------

* Modification de la méthode de coût pour l'uniformiser entre toutes les sociétés (si le module of_base_multicompany est installé)

* Ajout d'un champ pour mettre à jour le coût des articles de la catégorie suite aux mouvements de stock

* Ajout d'un champ pour mettre à jour le coût des articles de la catégorie suite aux imports

* Ajout d'un champ "Coût pour les ventes" qui permet de choisir entre :
  - le coût standard ;
  - le coût théorique.

Produits
--------

* Ajout d'un champ "Coût théorique" qui correspond au coût calculé par application des règles définies dans la marque
  ou dans les fichiers d'import.
  - Cette valeur de coût peut servir pour le calcul de la marge dans les devis et les factures ;
  - Elle n'est en revanche jamais utilisée pour la valorisation de l'inventaire.

Reporting
#########

* Modification du rapport de facturation :
  - Ajout de la marque des produits
  - Mise en place de deltas sur la quantité, le montant hors-taxe par rapport à la période précédente
