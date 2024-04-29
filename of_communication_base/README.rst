========================
OF Company communication
========================

Ce module permet de gérer les messages de communication de l'entreprise et de les publier sur OpenFire.
Ce module représente la partie diffuseur de message de l'entreprise.
Ce module permet de gérer les messages de communication de l'entreprise et c'est employer.

Fonctionnalités
###############

Communication (`of.communication.message`)
------------------------------------------

* Ajout d'un objet message de communication pour la création de message à publier
    - il possède différents champs pour la gestion du message :
        - Titre;
        - Résumé (texte simple, obligatoire, ne doit pas dépasser 280 caractères);
        - Contenu (texte HTML, optionnel);
        - Date de début de publication (permets de définir la date de début de publication du message sur OpenFire);
        - Date de fin de publication (permets de définir la date de fin de publication du message sur OpenFire);
        - Date de fin de vie (permet de définir la date auquel le message disparaîtra de la basse fille);
        - Type de message (information, alerte, événement, etc.);
        - Style de message (bandeau, popup);
        - État (brouillon, publié, en édition, annulé);
        - Renvoyer la notification (boolean qui permet de forcer ou non l'apparition de la notification, après une modification, sur la base fille);

* Ajout de l'objet log de notification pour créer un log de notification liée a un objet message
    - il possède différent champs pour la gestion des log de notification :
        - ID user (Many2one avec res.user)
        - ID message (Many2one avec of.communication)
        - Type d'action (vu ou pas vu)
        - Horodatage (Date de création du log)
        - Est marqué comme lu (boolean pour définir si la notification a été lue ou non)
        - Rappel est activer (boolean pour définir si la notification sera renvoyer)

* Un bouton de publication permet de publier le message sur OpenFire à la date de début de publication.
    - un message publié sera récupéré sur les bases de données OpenFire à partir de la date de début de publication et jusqu'à la date de fin de publication.
    - le message sera supprimé de la base de données OpenFire à la date de fin de publication;
    - il est possible de publier en masse plusieurs messages à la fois depuis la liste des messages;

* Un bouton d'annulation permet d'annuler la publication du message sur OpenFire.
    - un message annulé ne sera pas récupéré sur les bases de données OpenFire;
    - il n'est pas possible de publier un message annulé, ou d'annuler un message publié.

* Un bouton d'édition permet de modifier le message.
    - un message en cours d'édition sera supprimé des bases de données OpenFire le temps de l'édition.

* Ajout d'un composent définissant des model de notification et du message
    - il possède deux model de notification :
        - Une notification Bannière 
        - Une notification Pop-Up
    - il possède chacun un model de message

* Ajout de group pour activer/désactiver des fonctionnalités
    - Ajout de deux group : 
        - Un group qui peut consulter les message interne a l'entreprise
        - Un group qui peut créer des messages interne a l'entreprise

* Ajout d'un Cron qui renvoie les notification

