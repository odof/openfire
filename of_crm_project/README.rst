==============
OF crm project
==============

Module de gestion des projets dans le CRM

Fonctionnalités
###############

* Un menu "Projets" est ajouté dans le menu "Configuration" de l'application CRM
    - il est possible d'y configurer les modèles de projets, les attributs de projets et les valeurs d'attributs de projets

* Mise en place d'un onglet "Projet" dans les opportunités
    - il est possible de choisir un modèle de projet à partir duquel les "questions du projet" seront chargées sur l'opportunité;
    - il est possible de répondre aux questions directement sur l'opportunité;
    - le but étant de qualifier l'opportunité en fonction des réponses aux questions du projet.

* Création d'un objet modèle de projet
    - les modèles de projets contiennent une liste d'attributs qui seront reportés dans une fiche projet CRM sur sélection d'un modèle.

* Création d'un objet d'attribut de projet
    - un attribut de projet correspond à un 'champ' d'une fiche projet CRM, il possède un libellé et un type;
    - les types possibles sont 'Texte Court', 'Booléen', 'Date' et 'Choix Unique';

* Création d'un objet valeur d'attribut de projet
    - les valeurs d'attributs de projet correspondent aux valeurs possibles pour les attributs de type 'Choix Unique';
