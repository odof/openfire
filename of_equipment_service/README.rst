====================
OF Equipment Service
====================

Module de gestion des équipements pour les demandes d'intervention pour OpenFire.


Fonctionnalités
###############


Équipements (`of.equipment`)
----------------------------

* Ajout de différents smart buttons pour les équipements :
    - **DI Maintenance** : permet de visualiser les demandes d'intervention de type "Maintenance" liées à l'équipement.
    - **DI SAV** : permet de visualiser les demandes d'intervention de type "SAV" liées à l'équipement.
    - **DI à planifier** : permet de visualiser les demandes d'intervention de tous types à planifier liées à l'équipement.


Étapes (`of.service.request.stage`)
-----------------------------------

* Ajout d'un champ "État" sur les étapes des demandes d'intervention.
    - ce champ permet de définir l'état de l'étape.
    - les valeurs possibles sont "Brouillon", "En cours", "En attente", "Terminé" et "Annulé".
    - ce champ est utilisé pour calculer les délais de prise en compte et de gestion des demandes d'intervention.


Demande d'intervention (`of.service.request`)
---------------------------------------------

* Ajout d'un booléen **"Équipement"** et d'une **"liste d'Équipements"** sur les demandes d'intervention.
    - lorsque le booléen est coché, la liste d'équipements est affichée et permet de sélectionner les équipements liés à la demande d'intervention.
    - les équipements sélectionnées seront les équipements référents pour une intervention si cette dernière est créée à partir de la demande d'intervention.

* Ajout d'une liste des interventions d'équipements (`of.service.request.equipment.line`) sur la DI.
    - cette liste est **visible** dans **l'onglet "Interventions"** dans le formulaire de la DI.
    - elle **permet de visualiser les interventions liées** à un équipement référent de la DI.
    - **lorsqu'une intervention est créée ou modifiée** les lignes de cette liste sont **mises à jour** en conséquence :
        - lors de la création d'une intervention, une ligne est créée dans cette liste pour chaque équipement référent de la DI sélectionnée dans l'intervention.
        - si un **équipement** est **ajouté** à l'intervention, une ligne est **créée** dans cette **liste**.
        - si un **équipement** est **supprimé** de l'intervention, la ligne correspondante est **supprimée** de cette **liste**.

* Ajout d'un champ **"Payeur"** sur les demandes d'intervention.
    - les valeurs possibles sont **"Client", "Revendeur" et "Fournisseur"**.

* Ajout de champs délais sur les demandes d'intervention qui ne sont visibles que si le type de demande d'intervention est "SAV" :
    - **"Temps de prise en compte (heures)"** : C'est le temps entre la date de création de la DI et le passage de la DI dans l'étape Kanban avec l'état "En cours".
    - **"Temps de gestion (heures)"** : C'est le temps entre la date de création de la DI et le passage de la DI dans l'étape Kanban avec l'état "Terminé".

* Lors de la création d'une intervention depuis une DI, les équipements référents de la DI sont ajoutés à l'intervention.


Interventions (`calendar.event`)
--------------------------------

* Modification du **domaine de la liste des équipements** en fonction de la **DI sélectionnée** :
    - si jamais une **DI est renseignée**, les **équipements** sélectionnables sont ceux **liés à la DI et pas déjà pris en compte dans une autre intervention de cette DI**.
    - si jamais une **DI n'est pas renseignée**, les équipements sélectionnables sont ceux **liés au client ou à l'adresse de l'intervention**.

* Lors de la **création d'une intervention** avec un équipement **si une DI est renseignée**, l'**équipement** sera **ajouté à la liste des équipements** par interventions de la DI.

* Lors de la **modification des équipement d'une intervention** liée à une DI, les équipements ajoutés/supprimés seront **ajoutés/supprimés de la liste des équipements** par interventions de la DI.


Reporting
#########

* Ajout du détail des équipements sur les rapports de demandes d'intervention.
