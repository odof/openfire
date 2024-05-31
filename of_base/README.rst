==========
OF base
==========


Fonctionnalités
################

* Ajout des colonnes destinataire et partenaire dans la vue liste des emails.

* Ajout onglet historique dans formulaire partenaire.

* Ajoute la référence du produit dans la vue liste.

* Retire la couleur de fond aléatoire de l'image mise par défaut à la création d'un partenaire.

* Affiche l'adresse du contact dans le menu déroulant de sélection d'un partenaire.

* Affiche l'adresse au format français par défaut quand le pays n'est pas renseigné et non le format US.

* Ajout de la recherche multi-mots pour les articles.

* Désactive l'envoi des notifications par courriel des changements d'affectation des commandes et factures.

* Restreint l'accès au menu "Applications" à l'utilisateur administrateur.

* Soumet la désinstallation de module à une validation par mot de passe.

  Le hash du mot de passe doit être placé dans le fichier de configuration sous le nom 'of_module_uninstall_password'.

  Calcul du hash en python :
   .. code-block:: python

     from passlib.context import CryptContext; CryptContext(['pbkdf2_sha512']).encrypt("mon_mot_de_passe")


* API fonction permettant d'afficher un message dans une fenêtre au cours de l'exécution d'une fonction.

* Ajout d'un champ calculé et d'un bouton sur les actions d'envoi de mail pour avoir une pré-visualisation du mail.

* Permet à l'auteur d'un mail de le recevoir en copie (par défaut odoo retire l'expéditeur de la liste des destinataires).

* Nouvelle gestion des numéros de téléphone des partenaires avec formatage automatique des numéros.
  - Librairie Python phonenumbers nécessaire, pour installer :

  .. code-block:: bash

     pip install phonenumbers

* Ajout de la possibilité de ne pas afficher les menus qui sont affectés au menu spécial OF "Groupe spécial caché"

* Mise en place d'un type d'utilisateur Odoo pour catégoriser les utilisateurs dans Odoo (web, mobile, etc.)

* Ajout d'un modèle servant de log interne :
    - Titre : Généralement lié au nom du module;
    - Type d'erreur : Si erreur de validation par un connecteur alors catégorie de l'erreur (si présente) autrement définie par le développeur;
    - Modèle : Modèle dans lequel l'erreur s'est produite;
    - Fonction : Fonction dans laquelle l'erreur s'est produite;
    - Message : Si erreur de validation par un connecteur alors message retourné par l'erreur (si présent) autrement défini par le développeur;
    - Niveau de log : Peut être Info, Avertissement ou Erreur.

* Surchage du code standard Odoo pour gérer l'addition de groupes dans les attributs champs de la vue XML.

* Ajout d'un composant pour afficher la version actuelle de l'application.
    - cette version sera visible dans le "Systray" (zone de notification) d'Odoo à côté de l’icône des notifications/activités.
    - pour se faire **la version** doit être définie dans le **fichier `.openfire-version`** dans le répertoire racine **contenant `odoo`et le repo `openfire`**.
        - exemple :

          .. code-block:: bash

            $ ls
            $ odoo oca openfire .openfire-version
            $ cat .openfire-version
            16.0.1.0
      - si le fichier n'existe pas, le composant affichera "?!".


Droits utilisateurs
###################

* Ajout d'un groupe utilisateur **"Intranet"**
    - permet de donner les droits d'accès à l'intranet

* Ajout d'un groupe **"Groupe spécial caché"**
    - permet de cacher les éléments qui lui sont affectés

* Ajout d'un groupe **"Admin seulement"**
    - permet de cacher les éléments qui lui sont affectés aux utilisateurs non administrateurs

* Ajout d'un groupe **"Modifier le contrat OpenFire"**
    - permet de donner accès aux utilisateurs pouvant opérer des modifications impactant le contrat OpenFire
