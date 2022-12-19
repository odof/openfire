=================
OF Product brand
=================


Module OpenFire pour gérer la marque des produits
-------------------------------------------------
* Ajout de l'objet "Marque" et ses fonctionnalités :
   * Complétion automatique sur le champ "Marque" des produits en fonction du code produit
   * Synchronisation automatique entre le code d'une marque et le code produit des produits liés
   * Description de la marque (champ libre) reprise dans la description de la ligne de commande, de facture
     selon la configuration de cette dernière
   * Etc.
* Ajout du champ "Marque" dans les produits (champ obligatoire)
* Ajout d'une marque par défaut "Mon entreprise"
* Modification du rapport de ventes :
   * Ajout de la marque des produits
   * Affichage du montant livré
   * Mise en place des deltas sur la quantité, le montant hors-taxe et marge par rapport à la période précédente
* Modification du rapport d'achats :
   * Ajout de la marque des produits
* Modification du rapport de facturation :
   * Ajout de la marque des produits
   * Mise en place de deltas sur la quantité, le montant hors-taxe par rapport à la période précédente
* Ajout d'un wizard pour modifier la marque des produits en masse