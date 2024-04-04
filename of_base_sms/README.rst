===========
OF Base Sms
===========


Module OpenFire de liaison entre `of_base` et `sms`
---------------------------------------------------

Ce module a pour but de gérer le conflit entre le module Odoo standard `sms` et notre module `of_base`.

Le module `sms` réalise un replace d'un champ "Téléphone" que nous altérons dans `of_base` pour le remplacer une O2M.

Quand le module SMS est installé, par exemple via le paramètre de configuration `default_productivity_apps`, et bien un erreur apparait lors de l'installation de `of_base`.
