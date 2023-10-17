=========================
OF invoice report setting
=========================

Ce module permet la mise en place de lignes de groupement dans les totaux des rapports de facture.

Fonctionnalités
###############


Groupement de ligne de facture (`of.invoice.report.total.group`)
----------------------------------------------------------------

* Ajout d'un objet `of.invoice.report.total.group` permettant de définir les groupes de lignes de facture à afficher dans
  le rapport de facture.

* On crée un groupe de ligne de facture pour chaque type de ligne de facture à regrouper.

* Les groupes de ligne sont liés à une catégorie de produit ou à un produit.

* Les groupes de ligne de facture sont affichés dans l'ordre de leur position et en fonction de la positionnement "HT" ou
  "TTC".


Reporting
#########

* Modification du rapport de facture pour permettre de regrouper des lignes de factures dans les totaux.
  - le regroupement dépend de la configuration réalisée dans l'objet `of.invoice.report.total.group`;
  - il doit toujours rester au moins 1 ligne de facture.
