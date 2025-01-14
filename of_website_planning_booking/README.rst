===========================
OF website planning booking
===========================

Module de prise de RDV en ligne via le site web.

Fonctionnalités
###############

Parcours de prise de RDV en autonomie
-------------------------------------

Mise en place d'un outil de prise de RDV en autonomie accessible via le site web pour les clients avec ou sans accès portail.

* Première étape de saisie des informations nécessaires à la prise de RDV :

  - Choix d'une prestation à réaliser ou récupération d'un contrat existant (DI récurrente)
  - Saisie de l'adresse du client, et de sous-adresses pour les clients avec accès portail
  - Choix d'un créneau disponible à la demi-journée
  - Réponse au questionnaire :
    - Si la prestation choisie contient un questionnaire avec au moins une question définie comme devant être posée durant la prise de RDV en ligne, un bloc pour y répondre s'affiche
    - Saisie des réponses à toutes les questions définie comme devant être posée durant la prise de RDV en ligne, en une ou plusieurs étapes en fonction de la configuration du questionnaire

* Étape de confirmation :

  - Récapitulatif des informations saisies
  - Champ commentaire pour indiquer des informations supplémentaires
  - Accès aux conditions générales de vente
  - Validation du consentement d'être contacté par l'entreprise

* Un e-mail de confirmation est envoyé au client une fois le processus terminé

Intervention (`calendar.event`)
-------------------------------

Ajout de deux nouveaux champs sur les interventions :

* **Créé par le site web** permettant d'identifier les RDV pris via le prise de RDV en ligne
* **Doublon potentiel ?** qui reprend le champ du même nom du client du RDV afin de facilement identifier les doublons de contact créés depuis el site

Employé (`hr.employee`)
-----------------------

Ajout d'**Horaire Web** sur les employés. Permet de définir des horaires spécifiques à la prise de RDV en ligne pour les employés.
Si non renseigné, les horaires classiques seront pris en compte.

Créneaux disponibles (`of.planning.available.slot`)
---------------------------------------------------

Ajout d'un champ **Type** sur les créneaux disponibles, proposant deux valeurs : **normal** et **web**

* Le type **normal** est le type par défaut, utilisé pour les créneaux disponibles mis en place par le module des tournées
* Le type **web** permet d'identifier les créneaux disponibles correspondant aux horaires web des employés

Modèles d'intervention (`of.planning.intervention.template`)
------------------------------------------------------------

* Mise en place de la fonctionnalité de **publication pour le site web** afin d'identifier les modèle d'intervention qui seront accessibles en tant que prestation lors de la prise de RDV.

* Possibilité de définir un **libellé propre à la prise de RDV** pour chaque modèle publié.

Tournée (`of.planning.tour`)
----------------------------

* Adaptation du modèle de données des **tournées** afin de prendre en compte les créneaux disponibles de type web

* Re-calcul constant des créneaux disponibles de type web, à l'instar de ceux de type normal

Recherche de créneaux pour les tournées (`of.tour.appointment.wizard`)
----------------------------------------------------------------------

Mise en place d'une nouvelle notion sur l'assistant de recherche de créneaux pour être utilisé lors de la prise de RDV en ligne :

* Ajout de **Proposition de créneaux pour le site web** (`of.tour.appointment.line.website.wizard`) permettant de proposer les résultats de la recherche de créneaux sous forme de demi-journées
* À chaque proposition de créneau pour le site web, est rattaché plusieurs propositions de créneaux correspondant au résultat de la recherche
* Lors de la validation du processus de prise de RDV, les propositions de créneaux rattachées au choix de créneau pour le site web sont triés par distance utile.
  Une tentative de création de RDV est ensuite effectuée sur la première proposition de créneau, si entre-temps le créneau n'est plus disponible, le système passe à la proposition suivante.

Question du Questionnaire (`of.survey.question`)
------------------------------------------------

Ajout d'un champ **Depuis la prise de RDV en ligne ?** sur les questions de questionnaire. Si ce champ est coché, alors la question sera posée lors du processus de prise de RDV en ligne.

Paramètres de configuration
###########################

* Ajout d'un paramètre "(OF) Autorise les nouveaux clients" pour permettre la prise de RDV aux nouveaux clients :

  - Si ce paramètre est non coché, il est nécessaire de disposer d'un compte portail pour accéder à l'outil.
  - Cf. Paramètres > Intervention > Prise de RDV en ligne > **(OF) Autorise les nouveaux clients**.

* Ajout d'un paramètre "(OF) Société du partenaire pour les clients existants" pour permettre de définir que les RDV seront créés sur la même société que celles des clients existants.

  - Cf. Paramètres > Intervention > Prise de RDV en ligne > **(OF) Société du partenaire pour les clients existants**.

* Ajout d'un paramètre "(OF) Société des RDV" pour permettre de définir la société sur laquelle seront créés les RDV.

  - Cf. Paramètres > Intervention > Prise de RDV en ligne > **(OF) Société des RDV**.

* Ajout d'un paramètre "(OF) Configuration spécifique à cette société" permettant d'indiquer si le paramétrage de la prise de RDV en ligne est propre à la société courante de l'utilisateur

  - Cf. Paramètres > Intervention > Prise de RDV en ligne > **(OF) Configuration spécifique à cette société**.

* Ajout d'un paramètre "(OF) Jours ouverts" pour permettre de définir les jours de la semaine pour lesquels il sera possible de prendre un RDV en ligne.

  - Cf. Paramètres > Intervention > Prise de RDV en ligne > **(OF) Jours ouverts**.

* Ajout d'un paramètre "(OF) Techniciens disponibles" pour permettre de définir les techniciens et commerciaux qui seront en charge des RDV pris en ligne.

  - Cf. Paramètres > Intervention > Prise de RDV en ligne > **(OF) Techniciens disponibles**.

* Ajout d'un paramètre "(OF) Nombre de jours ouverts" pour permettre de définir le nombre de jours jusqu'où il sera possible de prendre des RDV en ligne.

  - Valeur maximale 180 jours.
  - Cf. Paramètres > Intervention > Prise de RDV en ligne > **(OF) Nombre de jours ouverts**.

* Ajout d'un paramètre "(OF) Mode de recherche" pour permettre d'indiquer le mode de recherche à prendre en compte pour la proposition des créneaux disponibles.

  - Valeurs possibles : Aller, Retour, Aller-Retour, Aller ou Retour, Aller si matin / Retour si après-midi
  - Cf. Paramètres > Intervention > Prise de RDV en ligne > **(OF) Mode de recherche**.

* Ajout d'un paramètre "(OF) Type de recherche" pour permettre d'indiquer le critère de recherche à prendre en compte pour la proposition des créneaux disponibles.

  - Valeurs possibles : Distance (km), Durée (min)
  - Cf. Paramètres > Intervention > Prise de RDV en ligne > **(OF) Type de recherche**.

* Ajout d'un paramètre "(OF) Critère de recherche max" pour permettre de définir la valeur maximale du critère de recherche à prendre en compte pour la proposition des créneaux disponibles.

  - Cf. Paramètres > Intervention > Prise de RDV en ligne > **(OF) Critère de recherche max**.

* Ajout d'un paramètre "(OF) Autorise la réservation sur des journées vierges" pour permettre d'indiquer s'il est possible de prendre un RDV en ligne sur une journée vierge.

  - Cf. Paramètres > Intervention > Prise de RDV en ligne > **(OF) Autorise la réservation sur des journées vierges**.

* Ajout d'un paramètre "(OF) Type de recherche pour les journées vierges" pour permettre d'indiquer le critère de recherche à prendre en compte pour la proposition des créneaux disponibles des journées vierges.

  - Valeurs possibles : Distance (km), Durée (min)
  - Cf. Paramètres > Intervention > Prise de RDV en ligne > **(OF) Type de recherche pour les journées vierges**.

* Ajout d'un paramètre "(OF) Critère de recherche max pour les journées vierges" pour permettre de définir la valeur maximale du critère de recherche à prendre en compte pour la proposition des créneaux disponibles des journées vierges.

  - Cf. Paramètres > Intervention > Prise de RDV en ligne > **(OF) Critère de recherche max pour les journées vierges**.

* Ajout d'un paramètre "(OF) État des RDV" pour permettre de définir l'état des RDV lors de leur création.

  - Valeurs possibles : Brouillon, Confirmé
  - Cf. Paramètres > Intervention > Prise de RDV en ligne > **(OF) État des RDV**.

* Ajout d'un paramètre "(OF) Afficher le prix de la prestation" permettant d'indiquer si le prix des prestations est affiché lors de la prise de RDV.

  - Le prix indiqué se base sur les lignes de facturation des modèles d'intervention
  - Cf. Paramètres > Intervention > Prise de RDV en ligne > **(OF) Afficher le prix de la prestation**.

* Ajout d'un paramètre "(OF) Fichier PDF des Conditions Générales de Vente" pour charger le fichier PDF des CGV qui sera accessible à l'étape de confirmation.

  - Cf. Paramètres > Intervention > Prise de RDV en ligne > **(OF) Fichier PDF des Conditions Générales de Vente**.

* Ajout d'un paramètre "(OF) Libellé horaires matin" pour permettre de définir la plage horaire des créneaux du matin qui sera affiché à l'étape de choix des créneaux.

  - Cf. Paramètres > Intervention > Prise de RDV en ligne > **(OF) Libellé horaires matin**.

* Ajout d'un paramètre "(OF) Libellé horaires après-midi" pour permettre de définir la plage horaire des créneaux du après-midi qui sera affiché à l'étape de choix des créneaux.

  - Cf. Paramètres > Intervention > Prise de RDV en ligne > **(OF) Libellé horaires après-midi**.

* Ajout d'un paramètre "(OF) Notes de confirmation de RDV" pour permettre de spécifier une note au format HTML qui sera visible à l'étape de confirmation.

  - Cf. Paramètres > Intervention > Prise de RDV en ligne > **(OF) Notes de confirmation de RDV**.
