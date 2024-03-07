==============
OF map view
==============

Module pour créer un nouveau type de vue (map view)


Fonctionnalités
###############


* Ajout d'un nouveau type de vue Carte (basé sur OpenStreetMap).

* Permet de placer des marker sur la vue carte en fonction de records auxquels la vue est associée.

* En cliquant sur le marker, cela affiche une pop-in sur le côté gauche de la carte qui contient des informations sur le record associé.
    -  en cliquant sur ce pop-in, cela redirige vers le formulaire de cet enregistrement.
    -  sinon il est possible de fermer la pop-in.

* Mise en place de fonctionnalités "MouseOver", "MouseOut" sur les markers :
    - cela permet d'afficher des tooltips au dessus des markers qui contiennent des informations;
    - cela permet  d'appliquer une coloration sur la pop-in ouverte liée au marker qui est survolé pour distinguer l'information rapidement.
