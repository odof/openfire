================
OF planning tour
================

Module de gestion de planification des interventions et de tournées pour les techniciens.

Fonctionnalités
###############

Tournée (`of.planning.tour`)
----------------------------

* Mise en place d'un modèle de données pour les **tournées** pour les techniciens :

  - Elles sont **composées de plusieurs interventions** et elles représentent un ensemble d'interventions à **réaliser** par un technicien **à une date donnée**.
  - Il n'y a donc qu'une seule tournée pour un même technicien à une même date.
  - Les tournées sont créées à la demande (dès qu'une intervention est créée pour des techniciens) ou automatiquement (via un cron de création de tournées pour les techniciens).

  - Dans une tournée, il est possible de visualiser :

    - Les interventions qui la composent dans une liste de lignes de tournées ;
    - Les informations de départ et d'arrivée du technicien ;
    - Le nombre de kilomètres total de la tournée ;
    - Le temps total de la tournée ;
    - L'itinéraire de la tournée représenté avec les différentes interventions sous forme de marqueurs et le tracé entre les interventions.

* Dans une tournée, il est possible de demander l'**optimisation** de l'itinéraire de cette dernière via un bouton "Optimiser".

  - Cela ouvrira un wizard qui permet de **visualiser** les informations de la tournée **avant et après l'optimisation** :

    - Le nombre de kilomètres total de la tournée ;
    - Le temps total de la tournée ;
    - L'itinéraire de la tournée avant et après l'optimisation pour constater les changements ;
    - Les interventions réordonnées dans la liste de lignes de tournées (nouveau créneau horaire, nouvelle distance entre les interventions, etc.).

  - L'**optimisation est réalisée par l'API de OSRM** (Open Source Routing Machine), selon l’algorithme du voyageur de commerce.
  - Lors de l'optimisation, nous **essayons de prendre en compte** les **horaires de l'employé** pour éviter de positionner une intervention en **dehors des horaires de travail** :

    - Si pendant l'optimisation, on se rend compte qu'il est possible de positionner une intervention pendant la pause déjeuner, un message d'avertissement est affiché pour prévenir l'utilisateur et lui laisser le choix de valider ou non cette position ;
    - Cependant, si les horaires n'étaient déjà pas respectés avant l'optimisation, nous ne cherchons pas à les respecter pendant l'optimisation.

  - L'utilisateur peut choisir de valider ou non l'optimisation de la tournée ;
  - Si jamais la tournée a été optimisée ou réorganisée, **un bouton de "restauration"** est disponible pour revenir au **dernier état connu de la tournée** avant l'optimisation ou la réorganisation ;
  - Si jamais une **donnée géographique** a **changé depuis la dernière optimisation**, un message d'avertissement est affiché pour prévenir l'utilisateur que la tournée a **besoin** d'une possible **nouvelle optimisation**. (Il est possible d'ignorer ce message).

* Dans une tournée, il est également possible de réorganiser la tournée via un bouton "Réorganiser".

  - Cela ouvre également un wizard, mais à la différence de l'optimisation, ici nous n'avons pas de carte, juste une liste de lignes de tournées à réordonner manuellement ;
  - Il n'y a pas de prévisualisation des informations réordonnées, il faut valider pour voir le résultat.
  - Ce wizard est donc un outil de réorganisation manuelle des interventions dans la tournée.

* Mise en place d'un cron de création de tournées pour les techniciens :

  - Ce cron permet de créer automatiquement les tournées vides pour les techniciens pour une période de jours donnée (option de configuration) ;
  - Ce cron s'exécute tous les jours et vérifie s'il doit ou non créer des tournées :

    - Si nous sommes dans la période de jours donnée, il crée les tournées vides pour les techniciens ;
    - Si jamais un employé est créé entre-temps, il crée les tournées vides pour ce nouvel employé jusqu'à la fin de la période de jours donnée ;
    - Il y a un nombre de jours "de sécurité" (10 jours) pour créer des tournées un peu plus loin que la période définie pour éviter de ne pas avoir de tournées pour les techniciens à la fin de la période.

* Sur la vue liste des tournées, il est possible de filtrer et de visualiser rapidement les tournées selon un code couleur :

  - En **noir** : les tournées **non confirmées** (tournée vide, brouillon, non optimisée) ;
  - En **gris** : les tournées **confirmées** ;
  - En **vert** : les tournées **optimisées** (une petite coche est également affichée en première colonne) ;
  - En **orange** : les tournées dont une **donnée géographique a changé** depuis la dernière optimisation, elles ont besoin d'une possible nouvelle optimisation (une petite icône d'avertissement est également affichée en première colonne) ;
  - En **rouge** : les tournées complètes.

Ligne de tournée (`of.planning.tour.line`)
------------------------------------------

* Les **lignes** de tournées sont les **interventions** qui composent une tournée :

  - Elles sont **créées lors de la création d'une intervention** et sont liées à une tournée.
  - Elles sont modifiées et ajustées lors de l'optimisation ou de la réorganisation de la tournée ou lors de la modification de l'intervention.
  - Elles ne peuvent pas être créées/modifiées/supprimées manuellement.

* Elles **portent les informations** techniques **importantes** pour la représentation de l'itinéraire complet de la tournée :

  - Ces informations sont :

    - Le temps de trajet entre l'intervention précédente et l'intervention actuelle ;
    - La distance entre l'intervention précédente et l'intervention actuelle ;
    - Le trajet entre l'intervention précédente et l'intervention actuelle (liste de coordonnées GPS) ;
    - La dernière ligne de la tournée contient donc aussi le tracé vers le point de retour de la tournée.

  - Ces informations sont donc constamment recalculées lors de la modification de la tournée ou de l'intervention.

Intervention (`calendar.event`)
-------------------------------

* Les interventions sont au cœur des tournées et provoquent la création/mise à jour des lignes de tournées dès qu'une donnée sensible est modifiée.

* Si une **tournée n'existe pas au moment de la création** de l'intervention, **une tournée est créée automatiquement** pour le technicien à la date de l'intervention :

  - Si une tournée existe déjà pour le technicien à la date de l'intervention, l'intervention est ajoutée à la tournée existante.

* Lors de la **modification** des champs **"Date de début"**, **"Date de fin"**, **"Durée"**, **"Adresse de l'intervention"**, **"Techniciens"** ou lors de son **changement d'état**, les lignes de tournées sont **recalculées** :

  - Si l'intervention est **déplacée à une autre date**, elle est **retirée** de la tournée actuelle et **ajoutée** à la tournée du technicien à la nouvelle date ;
  - Si la **durée** de l'intervention est **modifiée**, les **lignes** de tournées sont **recalculées** pour prendre en compte la nouvelle durée ;
  - Si l'intervention est **déplacée à une autre adresse**, les lignes de tournées sont **recalculées** pour prendre en compte le nouveau trajet ;
  - Si l'intervention est **déplacée à un autre technicien**, elle est **retirée** de la tournée actuelle et **ajoutée** à la tournée du nouveau technicien ;
  - Si un **nouveau technicien** est ajouté à l'intervention, elle est **ajoutée** à la tournée du nouveau technicien ;
  - Si les **coordonnées GPS** de l'adresse de l'intervention **sont modifiées**, les lignes de tournées sont **recalculées** pour prendre en compte le nouveau trajet.

* Lors de la suppression, de l'annulation ou du report d'une intervention, l'intervention est retirée de la tournée concernée.

Demande d'intervention (`of.service.request`)
---------------------------------------------

* Ajout d'un bouton "Planifier" sur le formulaire d'une demande d'intervention, ce bouton permet d'ouvrir un wizard de planification :

  - Ce wizard permet de rechercher les créneaux horaires disponibles pour les techniciens pour la date de la demande d'intervention (DI), pour une tâche donnée, pour une durée donnée, pour un technicien donné ;
  - Ce wizard affiche également une carte qui permet d'afficher la DI en l'incluant dans l'itinéraire de la tournée si elle existe ;
  - Pour chacun des créneaux disponibles remontés par le wizard, il est possible de visualiser les informations de la tournée (distance, temps, itinéraire) via un bouton "Aperçu" ;
  - L'utilisateur a donc un écran de recherche de créneaux avec toutes les informations nécessaires pour choisir le meilleur créneau qui lui convient.

Créneaux disponibles (`of.planning.available.slot`)
---------------------------------------------------

* Un **créneau disponible** est une **période de temps de travail** durant laquelle un **technicien est libre**.

* La **durée du créneau** doit être au moins équivalente à la **durée de la tâche la plus courte de la base**.

* Un **créneau disponible est créé** à partir du moment où :

  - Une **intervention est placée** sur une journée travaillée d’un technicien ;
  - La **durée minimale du créneau est respectée** entre :

    - Le début de la disponibilité (démarrage de la journée ou intervention précédente) ;
    - La fin de la disponibilité (fin de la journée ou début de l’intervention suivante) ;

  - La **différence entre la durée** du créneau et **le temps de trajet de l'intervention suivante** doit au moins être **égale** à la **durée minimale d’un créneau** (durée de tâche la plus courte sur la base) ;
  - Sans intervention, la journée est considérée comme disponible sur les horaires travaillés du technicien.

* Ils sont utilisés pour déterminer les créneaux horaires disponibles lors de la planification d'une demande d'intervention (DI) :

  - Ils permettent une recherche rapide des créneaux pour la DI en prenant en compte les horaires de travail du technicien car ils sont précalculés en amont de la planification.

* Un créneau est **lié à une tournée** qui a la responsabilité de certaines informations comme :

  - Employé ;
  - Tâches (compétences des employés) ;
  - Date ;
  - Secteur.

* Comme pour les tournées, ils sont **recalculés constamment** dès lors qu'un des **champs sensibles** ("Date de début", "Date de fin", "Durée", "Adresse de l'intervention", "Techniciens" ou "État") d'une intervention **est modifié**.

* Il est possible de visualiser les créneaux disponibles depuis :

  - Le formulaire d'une tournée via un onglet "Créneaux disponibles" ;
  - Le menu "Interventions > Configuration > Créneaux disponibles" pour visualiser tous les créneaux disponibles pour les techniciens.

* Un **cron d'archivage passe tous les jours** pour archiver les créneaux disponibles passés pour les techniciens.

* Un **cron de nettoyage passe tous les 14 jours** pour supprimer les créneaux disponibles dont la date de fin est passée depuis plus de 14 jours.

Modèle de recherche de créneaux (`of.tour.appointment.template`)
----------------------------------------------------------------

* Les modèles de recherche de créneaux permettent de définir des modèles de recherche de créneaux pour les techniciens :

  - Ils sont utilisés lors de la planification d'une demande d'intervention (DI) pour faciliter la recherche de créneaux horaires disponibles.
  - Ils permettent de définir des critères de recherche pour les créneaux horaires disponibles :

    - La tâche de la DI (et donc la durée) ;
    - Les techniciens en mesure de réaliser la tâche ;
    - Le mode de recherche (aller, retour, aller-retour, aller ou retour, aller si matin ou retour si après-midi) ;
    - Etc.

* Il est possible de définir les utilisateurs qui peuvent utiliser le modèle de recherche de créneaux via le champ "Accessible pour" :

  - Si aucun utilisateur n'est défini, le modèle est disponible pour tous les utilisateurs.
  - Les utilisateurs non définis dans la liste ne verront pas le modèle de recherche de créneaux lors de la planification d'une DI.

Droits utilisateurs
###################

* Mise en place de deux groupes "(OF) Création manuelle de tournée autorisée" et "(OF) Création manuelle de tournée non autorisée" pour permettre ou non la création manuelle de tournée depuis la vue liste des tournées :

  - Ces groupes sont contraires et donc un utilisateur ne peut appartenir qu'à un seul des deux groupes.
  - Ces groupes sont accessibles via des paramètres de configuration. (Cf. Paramètres de configuration).

Paramètres de configuration
###########################

* Ajout d'un paramètre "(OF) Mode de recherche" pour permettre le mode de recherche par défaut lors de la planification d'une DI :

  - Ce mode est utilisé s'il n'existe pas de modèle de recherche de créneaux dans la base.
  - Cf. Paramètres > Intervention > Planification d'intervention > **(OF) Mode de recherche**.

* Ajout d'un paramètre "(OF) Type de recherche" pour permettre le type de recherche par défaut lors de la planification d'une DI :

  - Ce mode est utilisé s'il n'existe pas de modèle de recherche de créneaux dans la base.
  - Cf. Paramètres > Intervention > Planification d'intervention > **(OF) Type de recherche**.

* Ajout d'un paramètre "(OF) Modèle d'intervention par défaut pour la recherche" pour permettre de définir le modèle de recherche de créneaux par défaut lors de la planification d'une DI :

  - Cf. Paramètres > Intervention > Planification d'intervention > **(OF) Modèle d'intervention par défaut pour la recherche**.

* Ajout d'un paramètre "(OF) Tournées // Créer des tournées sur __ jours" pour permettre de définir le nombre de jours pour lesquels les tournées doivent être créées pour les techniciens :

  - Cf. Paramètres > Intervention > Tournées > **(OF) Tournées // Créer des tournées sur __ jours**.

* Ajout d'un paramètre "(OF) Tournées // Employés" pour permettre de définir les employés pour lesquels les tournées doivent être créées via le cron :

  - Cf. Paramètres > Intervention > Tournées > **(OF) Tournées // Employés**.

* Ajout d'un paramètre "(OF) Création manuelle de tournée autorisée" pour autoriser la création manuelle de tournée depuis la vue liste des tournées :

  - Ce paramètre provoquera l'ajout de tous les utilisateurs dans le groupe "(OF) Création manuelle de tournée autorisée".
  - Cf. Paramètres > Intervention > Tournées > **(OF) Création manuelle de tournée autorisée**.
