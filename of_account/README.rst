==========
OF account
==========

Module de comptabilité pour OpenFire.


Fonctionnalités
################

Client
------

* **Modification du système d'avertissement** et mise en place du socle technique et fonctionnel pour différents objets (facture, commande, etc.)
    - adaptation du fonctionnement Odoo standard pour permettre d'activer un message d'avertissement sur un objet;
    - une liste de choix apparait sur la fiche client pour permettre d'activer ou non l'avertissement pour les commandes ou les factures

* Ajout d'un message d'avertissement si le compte client est modifié alors qu'il existe déjà des écritures comptables saisies sur ce dernier


Compte
------

* Ajout d'un **compte de contre partie**
    - lors de la saisie d'une pièce comptable de type "achat", le compte de contre partie de la 2eme ligne est automatiquement renseigé en fonction du compte de la 1ere ligne si elle en a un.

* Ajout d'un champ booléen **"Éditable"** (par défaut à True)
    - seul l'administateur peut modifier un compte marqué comme non éditable.


Journal
-------

* Un journal qui n'est pas de type "vente", "banque" ou "espèce" sera automatiquement marqué comme "Verrouiller les écritures comptabilisées avec hash"
    - il ne sera plus possible de modifier les écritures comptabilisées sur ce journal;
    - un batch est mis en place pour changer la valeur des journaux existants si besoin;
    - seul l'administateur peut voir et modifier la valeur de ce champ.


Pièce comptable et écriture comptable
-------------------------------------

* Mise en place d'aide à la saisie sur les pièces comptables :
    - récupération du compte de contre partie en fonction du compte de la 1ere ligne;
    - récupération du compte du client saisi sur la 1ère ligne :
        - pour un journal de type "achat" on prend le compte tiers fournisseur;
        - pour un journal qui n'est pas de type "vente" on prend le compte tiers fournisseur, s'il n'est pas également client;
        - pour les autres journaux on prend le compte tiers client;
    - récupération du client en fonction des lignes saisies;
    - récupération de la date de la dernière pièce comptable saisie sur ce journal.

* Possibilié de saisir une pièce comptable de type "Banque" via le menu des pièces comptables "génériques"
    - un paramètre système permet de définir les journaux séléctionnables pour ce type de pièce comptable.

* Affichage de la balance dans la liste des lignes d'écriture

* Lors de la reconciliation d'un paiement, le libellé de la ligne d'écriture est modifié pour afficher le numéro de la facture et le nom du client sous la forme :
    - "[30 premiers caractère du Nom du client] [Numéro de la facture]".


Facture et avoir
----------------

* Ajout d'un contrôle pour empêcher la validation d'une facture avec un montant négatif

* Ajout d'une vue formulaire pour les lignes de factures

* Ajout d'un bouton sur les lignes de factures pour **permettre d'ouvrir la ligne en vue formulaire**

* Ajout d'un champ **"Exporté"** pour savoir quelles pièces comptables ont été exportées
    - un wizard permet de marquer les factures comme "Exportées".

* Ajout des informations client comme les numéros de téléphone et l'adresse email dans les factures

* Ajout du champ **"Étiquettes client"** et permettre de rechercher les factures par étiquettes client

* Déplacement du champ **"Position fiscale"** dans l'entête de la facture sous la date de facturation

* **Affichage de la balance** dans la liste des lignes d'écriture de la facture

* Permettre de modifier la date d'échéance manuellement même si une condition de réglement est définie

* Le champ "Produit" sur les lignes de facture n'affichera que le code produit si il est présent
    - c'est pour limiter l'affichage d'information en doublon avec le champ "Description".

* Ajout du champ **"Catégory produit"** sur les lignes de factures

* Ajout du champ **"Date de facture"** sur les lignes de factures

* Ajout des champs "Prix unitaire HT" et "Prix unitaire TTC" sur les lignes de factures
    - le champ "Prix unitaire HT" est affiché sur la vue formulaire des lignes de factures si il est différent du prix unitaire standard.

* Lors la facture est "Comptabilisée", le libellé de la ligne d'écriture est modifié pour afficher le numéro de la facture et le nom du client sous la forme :
    - "[30 premiers caractère du Nom du client] [Numéro de la facture]";
    - si c'est une facture d'achat le champ référence de la facture est également affiché.

* Ajout de la possibilité de grouper les lignes de facture en fonciton de l'étiquette client


Condition de règlement
----------------------

* Ajout d'un champ **"Condition de réglement pour la facture de solde"** sur les conditions de règlement
    - cette condition sera automatiquement utilisée pour les factures de solde sur un devis ayant des acomptes.

* Ajout d'un champ **"Description"** sur les lignes de conditions de reglement
    - prendra par défaut la valeur "Solde";
    - cette description est utilisée pour l'affichage de l'échéancier dans les commandes.



Droits utilisateurs
###################

* Ajout d'un groupe **"(OF) Peut modifier les comptes avec des lignes d'écriture"**
    - il n'est pas possible de modifier le code d'un compte comportant des lignes d'écriture, sauf si l'utilisateur fait partie de ce groupe



Paramètres de configuration
###########################

* Ajout d'un paramètre pour choisir une condition de réglement à utiliser pour les factures d'acompte
    - c'est un paramètre société dépendant;
    - cette condition de réglement sera donc automatiquement utilisée pour les factures d'acomptes;
    - si ce paramètre n'est pas renseigné, la condition de règlement du devis sera utilisée.
