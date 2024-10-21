====================
OF Equipment Service
====================

Module de gestion des équipements pour les demandes d'intervention dans OpenFire.

Fonctionnalités
###############

Équipements (`of.equipment`)
----------------------------

- Ajout de différents smart buttons pour les équipements :
    - **DI Maintenance** : permet de visualiser les demandes d'intervention de type "Maintenance" liées à l'équipement.
    - **DI SAV** : permet de visualiser les demandes d'intervention de type "SAV" liées à l'équipement.
    - **DI à planifier** : permet de visualiser les demandes d'intervention de tous types à planifier, liées à l'équipement.

Étapes (`of.service.request.stage`)
-----------------------------------

- Ajout d'un champ **"État"** sur les étapes des demandes d'intervention :
    - Ce champ permet de définir l'état de l'étape.
    - Les valeurs possibles sont : "Brouillon", "En cours", "En attente", "Terminé" et "Annulé".
    - Ce champ est utilisé pour calculer les délais de prise en compte et de gestion des demandes d'intervention.

Demande d'intervention (`of.service.request`)
---------------------------------------------

- Ajout d'une liste des équipements liés à une demande d'intervention (DI) :
    - Cette liste est visible dans la section **"Quoi"** de la DI, si la case **"Équipements"** est cochée.
    - Il est possible d'ajouter un équipement individuellement ou en masse via le smart button **Ajouter des équipements**.
    - Il est possible d'ajouter plusieurs fois le même équipement à une DI.
    - Lors de l'ajout, un rapport d'équipement spécifique peut être associé à chaque équipement.

- Calcul de la durée de la DI en tenant compte des équipements liés :
    - **Formule** : ([Durée de la tâche de la DI] × [Nombre de liens d'équipements sans tâche]) + [Somme des durées des tâches des liens d'équipement].

- Synchronisation des équipements entre DI et intervention :
    - **Modification** : Toute modification d'une ligne d'équipement dans une DI ou une intervention est répercutée sur l'autre, avec ajout d'un message dans le fil de discussion.
    - **Ajout** : Lorsqu'une ligne d'équipement est ajoutée à une intervention, elle est également ajoutée à la DI liée, avec un message dans le fil de discussion.
    - **Suppression** : La suppression de liens d'équipements n'est pas synchronisée et doit être effectuée manuellement.

- Restrictions sur les DI terminées ou annulées :
    - Il n'est plus possible de modifier la liste des équipements si la DI est dans l'état **"Terminé"** ou **"Annulé"**.

- Ajout d'une liste des interventions liées à une DI :
    - Cette liste, visible dans l'onglet **"Interventions"**, permet de suivre les interventions liées aux équipements de la DI.
    - Les lignes de cette liste **sont mises à jour automatiquement** :
        - Lors de la création d'une intervention, une ligne est créée pour chaque équipement référencé dans la DI.
        - Les modifications d'équipements dans l'intervention sont reflétées dans cette liste.

- Lors de la création d'une intervention à partir d'une DI, les équipements de la DI sont automatiquement ajoutés à l'intervention.

- Ajout d'un champ **"Payeur"** sur les DI :
    - Valeurs possibles : **"Client"**, **"Revendeur"**, **"Fournisseur"**.

- Ajout de champs pour les délais des DI de type **SAV** :
    - **"Temps de prise en compte (heures)"** : Temps entre la création de la DI et son passage à l'étape Kanban avec l'état **"En cours"**.
    - **"Temps de gestion (heures)"** : Temps entre la création de la DI et son passage à l'étape Kanban avec l'état **"Terminé"**.

Interventions (`calendar.event`)
--------------------------------

- Filtrage des équipements dans une intervention en fonction de la DI associée :
    - Si une DI est renseignée, seuls les équipements liés à cette DI et non encore pris en compte dans une autre intervention de la même DI sont sélectionnables.
    - Si aucune DI n'est renseignée, les équipements liés au client ou à l'adresse de l'intervention sont sélectionnables.

- Synchronisation entre intervention et DI :
    - Lors de la création d'une intervention avec une DI renseignée, les équipements de la DI sont ajoutés à l'intervention.
    - Les modifications des équipements dans une intervention sont reflétées dans la liste des équipements de la DI associée.

Reporting
#########

- Ajout du détail des équipements sur les rapports des demandes d'intervention.
