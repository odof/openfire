========
OF sale
========

Module de gestion des ventes pour OpenFire.


Fonctionnalités
################

Clients
-------

* Ajustement du système de **message d'avertissement** sur les fiches clients pour y ajouter l'option des commandes

* Mise en place d'une **politique de facturation par défaut** pour les commandes sur la fiche client :
    - facturation sur les quantités commandées;
    - facturation sur les quantités livrées.


Produits:
---------

* Modification de **la vue des produits ouverte par défaut depuis le menu "Ventes > Produits > Produits""**, c'est la vue liste qui est ouverte par défaut et non plus la vue kanban


Ventes
------

* Mise en place du socle technique pour les vérifications à effectuer lors de la confirmation de commande
    - le bouton standard de confirmation de commande est remplacé par un bouton personnalisé qui permet de faire les vérifications et de confirmer la commande si tout est ok.

* Ajout du switch **mode vendeur/mode client** dans la vue du formulaire de commandes

* Ajout des **informations détaillées** comme le numéro de téléphone (mobile, fixe), l'email du client dans la vue formulaire de la commande

* Ajout de l'information **d'obsolèsence du produit** dans les vues liste/formulaire des lignes de commande

* Ajout de l'information de la **date du tarif** dans la vue formulaire des lignes de commande

* Ajout d'un bouton pour permettre **l'ouverture de la vue formulaire d'une ligne** alors que la commande n'est pas encore confirmée

* Ajout d'une **date de facturation estimée** sur les commandes de ventes :
    - cette date est calculée en fonction de la politique de facturation choisie;
    - si la politique de facturation est **quantités commandées**, la date de facturation estimée est renseignée manuellement;
    - si la politique de facturation est **quantités livrées**, la date de facturation estimée est calculée automatiquement en fonction de la date prévue de livraison :
        - date de livraison prévue du premier picking non encore traité ou date de livraison prévue du dernier picking traité.

* Mise en place du socle fonctionnel de l'**article principal** :
    - ajout d'un champ **Article principal** sur les catégories d'articles;
    - ce champ est repris sur les lignes de ventes et permet de définir l'article principal de la commande.

* Modification du filtre des positions fiscales sur la commande de vente :
    - le filtre est maintenant sur les positions fiscales dont les taxes sources sont des taxes de vente.

* Affichage des **étiquettes du client** sur la commande de vente et permettre de **rechercher** sur ces étiquettes

* Modification de la vue de recherche des commandes de ventes :
    - ajout d'un filtre pour les commande de ventes totalement facturable;
    - ajout d'un filtre pour les commandes de vente non totalement livrées.

* Ajustement pour les **messages d'avertissements** d'une fiche client :
    - si le client n'a pas de message d'avertissement, nous controllons **si la fiche parente a un message d'avertissement** et nous l'affichons si c'est le cas;

* Ajout d'un mode **d'affichage étendue pour le nom de la commande** de ventes en fonction d'un contexte ("SOXXXXX - État - Date de la commande")

* Modification du calcul du prix unitaire de la ligne de commande pour prendre en compte le caractère "quantité dépendant" de la liste de prix:


Facturation
-----------

* Mise en place des articles verrouillés sur les lignes de factures (et lignes de commandes) pour éviter la modification / suppression de ces lignes depuis la commande
    - les lignes verrouillées sont synchronisées entre la commande et la facture;
        - seuls les champs "Prix unitaire", "UOM", "Remise" et "Taxes" sont synchronisés.



Droits utilisateurs
###################

* Ajout d'un groupe **"Responsable"** pour les droits de **gestion des ventes**
    - la hierarchie des droits est maintenant la suivante :
        - *Administrateur > Responsable > Utilisateur: tous les documents > Utilisateur: mes documents seulement*.

* Ajout de deux groupes **"(OF) Affichage des sous-totaux taxes excluses par ligne de commande client"** et **"(OF) Affichage des sous-totaux taxes incluses par ligne de commande client"** pour permettre d'afficher les sous-totaux HT ou TTC par ligne de commande client sur demande.
    - ces groupes sont accessibles via des paramètres de configuration. (cf. Paramètres de configuration).



Paramètres de configuration
###########################

Ventes
------

* Ajout d'un paramètre pour choisir une catégorie d'articles d'acompte
    - cf. Paramètres > Ventes > Facturation > **(OF) Catégorie d'articles utilisés pour les acomptes**;
    - cette catégorie sera utilisée à travers le wizard de facturation de commande pour filter/trouver l'article d'acompte à utiliser.

* Ajout d'un paramètre pour l'installation des options de ligne de commande
    - cf. Paramètres > Ventes > Devis & Commande > **(OF) Option de ligne de commande**.

* Ajout d'un paramètre pour rendre la position fiscale obligatoire
    - cf. Paramètres > Ventes > Facturation > **(OF) Position fiscale**.

* Ajout d'un paramètre pour activer l'ajout d'un devis additionnel sur une commande
    - cf. Paramètres > Ventes > Devis & Commande > **(OF) Devis supplémentaires**.

* Ajout d'un paramètre pour permettre de ne plus faire suivre les conditions de règlement lors de la facturation d'une commande
    - cf. Paramètres > Facturation > Factures clients > **(OF) Arrêter la propagation des conditions de paiement**;
    - si cette option est activée, la condition de règlement de la commande ne sera pas reprise sur la facture lors de sa création.

* Ajout de deux paramètres pour choisir d'afficher les sous-totaux HT ou TTC par ligne de commande client
    - cf. Paramètres > Ventes > Devis & Commande > **(OF) Affichage des sous-totaux taxes excluses par ligne de commande client**;
    - cf. Paramètres > Ventes > Devis & Commande > **(OF) Affichage des sous-totaux taxes incluses par ligne de commande client**;
    - ces paramètres sont utilisés "en parallèle du / en lisaison avec" le paramètre standard **Affichage du sous-total des lignes** (dans les paramètres de facturation);
    - le paramètre standard sera donc également modifié de façon automatique pour correspondre à la valeur choisie dans les paramètres OF
    - un message d'alerte sera affiché lors du changement de valeur du paramètre standard pour informer l'utilisateur de la modification automatique de ce paramètre.

* Ajout d'un paramètre pour rendre la facturation groupé configurable
    - cf. Paramètres > Ventes > Facturation > **(OF) Facturation groupée**;
    - le groupement par défaut dans Odoo est un groupement par société, client et devise.;
    - nous ajoutons la possibilité de choisir le groupement par commande.

* Ajout d'un paramètre pour activer le sous-type de message **E-mail** pour les commandes de ventes
    - cf. Paramètres > Ventes > Devis & Commande > **(OF) Activer l'abonnement au sous-type E-Mail pour les commandes de ventes**;
    - si cette option est activée, le sous-type **E-mail** sera disponible dans les commandes de ventes et l'email composer (*accessible via le bouton "Envoyer par email"*) diffusera le message à tous les abonnés de ce sous-type et non plus seulement aux abonnés de la commande;

* Ajout d'un paramètre pour choisir le mode de valorisation de la date de confirmation de la commande
    - cf. Paramètres > Ventes > Devis & Commande > **(OF) Mode de date de confirmation sur les ventes**;
    - il y a deux modes disponibles :
        - **automatique** : c'est le fonctionnement standard, la date de confirmation est mise à jour automatiquement lors de la confirmation de la commande;
        - **manuel** : la date de confirmation est renseignée manuellement par l'utilisateur lors du processus de validation de la commande;


Facturation
-----------

* Ajout d'un paramètre pour choisir la couleur de fond et la couleur de police des sections dans les rapports PDF
    - cf. Paramètres > Facturation > Impression PDF > **Titres de section**;

* Ajout d'un paramètre pour choisir le mode de gestion des BLs dans les factures
    - cf. Paramètres > Facturation > Factures clients > **(OF) Gestion des bons de livraison dans la facture client**;
    - il y a trois modes disponibles :
        - **Ne pas gérer les BL depuis la facture** : c'est le fonctionnement standard, les BLs ne sont pas gérés dans les factures;
        - **Gérer les BL après la validation de la facture** : les BLs liés à la commande/facture sont affichés sur la vue formulaire de la facture;
        - **Valider les BL au moment de la validation de la facture** : les BLs liés à la commandes/facture sont automatiquement validés lors de la validation de la facture.


Reporting
#########

* Mise en place d'un rapport pour la liste des commandes clients

* Modification du rapport standard **Devis/Commande** :
    - ajout de quelques identifiants techniques afin de permettre une modification plus facile par d'autre modules;
    - mise en place du socle concernant l'impression des prix.

* Modification du rapport standard **Facture** :
    - ajout de la coloration des titres de section (configuration dans les paramètres de comptabilité);
    - ajout de quelques identifiants techniques afin de permettre une modification plus facile par d'autre modules;
    - mise en place du socle concernant l'impression des prix.
