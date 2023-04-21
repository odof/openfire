=================
OF base location
=================


Module OpenFire extension du module OCA "Base location"
--------------------------------------------------------
Fonctionnalités :

* Ajout des coordonnées GPS à la structure des villes importées
* Ajout d'un objet "Secteur" pour définir des secteurs géographiques par rapport aux codes postaux

  * Les secteur peuvent être de type technique, commercial ou les deux.
  * Les secteur peuvent être liés à des partenaires
* Mise à jour en masse des secteurs des clients depuis la vue liste des clients ou depuis le secteur lui même


Ce module Nécessite l'installation du module **base_location_geonames_import** du dépôt partner-contact de l'OCA.

Pour faire l'import, aller dans *Contact > Configuration > Localisation > Importer de Geonames*
