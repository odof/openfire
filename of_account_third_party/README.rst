========
OF tiers
========

Module OpenFire / Comptes de tiers
----------------------------------


Fonctionnalités
################


Facturation
-----------


* Mise à jour du compte client/fournisseur lors de la saisie d'une facture.
    - cette mise à jour du compte se déroulera si :
        - le partenaire est marqué comme "est un client" ou "est un fournisseur";
        - si le compte "client/fournisseur" est celui par défaut de Odoo.


Paramètres de configuration
###########################

Comptes
-------

* Ajout de paramètres pour définir les templates de code pour les comptes clients et fournisseurs.
    - cf. Paramètres > Facturation > Comptes > **(OF) Code des partenaires**.
    - les champs "Code client" et "Code fournisseur" permettent de définir les expressions python qui seront utilisées pour générer les codes des comptes clients et fournisseurs.
