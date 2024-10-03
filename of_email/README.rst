========
OF email
========

Module de configuration et de gestion des emails pour OpenFire


Fonctionnalités
###############

* Ajout d'un champ "Forcer le Répondre à" dans les modèles de mail
    - ce champ permet de forcer l'adresse email vers laquelle les réponses seront redirigées lors de l'envoi d'emails avec le composeur de mail.
    - ce champ est mutuellement exclusif avec le champ "Répondre à" qui sera vidé si ce champ est renseigné.
    - ce champ n'est pas utilisé dans les envois en masse.
    - cela permet de ne pas altérer le fonctionnement standard du champ "Répondre à" qui est utilisé pour les envois en masse.
    - ce champ est pris en compte dans la prévisualisation des emails également.
