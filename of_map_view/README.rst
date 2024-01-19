==============
OF map view
==============

Module pour créer un nouveau type de vue (map view)


Fonctionnalités
###############


Contact
-------

* Affichage de la carte dans un nouveau type de vue xml pour les contacts.
* Placer les "markers" sur le map pour les contacts géolocalisés.
* En Mouseover de marker :
                - Afficher des popups sur les markers directement qui contiennent le nom et la précison de contact.
                - Colorer les popups qui sont en haut à gauche en jaune.
* En Mouseout de marker :
                - Fermer les petits popups qui sont directement sur les markers.
                - Colorer les popups qui sont en haut à gauche en blanc.

* En cliquant sur le marker , il va nous afficher le popup en haut à gauche qui contient le nom,
    l'adresse et le numéro de téléphone de contact.

* En Mouseover de popup en haut à gauche :
                - Colorer les markers en jaune.

* En Mouseout de popup en haut à gauche :
                - Colorer les markers en blanc.

* En cliquant sur le popup, qui est en haut à gauche, il va nous rediriger vers le fiche contact.
* En cliquant sur le croix , le popup va etre supprimé .
