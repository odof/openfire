===============
OF User Profile
===============

Module de gestion des profils utilisateurs

Fonctionnalités
###############

Utilisateur
-----------

* Ajout d'un booléen **"Est un profil utilisateur"** pour les utilisateurs :
    - Permet d'identifier un utilisateur comme étant un profil utilisateur;
    - Les profils utilisateurs ne peuvent pas se connecter à l'application;
    - Les profils utilisateurs servent de modèles pour la création d'autres utilisateurs.

* Ajout d'un champ **"Champ à mettre à jour"** :
    - Permet de définir les champs à synchroniser entre le profil utilisateur et l'utilisateur lié.

* Ajout d'un champ **"Profil utilisateur"** pour les utilisateurs :
    - Ce champ permet de lier un utilisateur à un profil utilisateur;
    - Un utilisateur ne peut être lié qu'à un seul profil utilisateur à la fois;
    - Les informations de l'utilisateur sont automatiquement synchronisées avec celles du profil utilisateur lié.
