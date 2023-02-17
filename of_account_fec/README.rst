======
OF FEC
======


Module OpenFire extension du module OCA "France - FEC Export"
-------------------------------------------------------------

* Ajout de la possibilité de choisir le format de l'export : TXT ou CSV

* Ajout de fonctionnalités supplémentaires pour les exports non officiels.

  Si jamais le type d'export est "Officiel" alors c'est le module OCA qui est utilisé, sinon c'est le module OpenFire qui est utilisé.

  Modifications effectuées pour les exports non officiels :

  * Ajout de la possibilité trier les lignes par "Date" ou par "Journal & Client"
  * Ajout d'un type d'export "Rapport FEC non officiel (entrées publiées uniquement)" qui s'affiche uniquement en mode
    test
  * Ajout du choix des journaux comptables à exporter
  * Ajout d'un paramètre pour choisir la date de l'écriture comptable à prendre en compte comme critère de sélection

    ::

      Certains clients ont besoin de prendre la date de création de l'écriture comptable à la place de sa date comme critère de sélection.
      Exemple pour des exports mensuels vers un outil de gestion externe.