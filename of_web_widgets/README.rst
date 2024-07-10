=============
OF Web Widget
=============

Ce module permet l'ajout de widget ou la customisation de widget existant.

Fonctionnalités
################

* Ajout d'un widget qui permet d'afficher une carte et des données dessus

  Utilisation :
    - <field name="partner_id" widget="of_partner_map"/> (Le champ doit être un many2one sur res.partner)

  Options possibles :
    - <field name="partner_id" widget="of_partner_map" options="{'map_rows' : 20}"/>

        * Par défaut, la hauteur du widget est à 4 (soit en gros 4x la taille d'une ligne de field standard).
        * Si on met 20, on aura donc 20x la taille d'une ligne de field standard.
