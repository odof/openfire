========
OF utils
========

Module OpenFire d'utilitaires
-----------------------------

* Ajout des objets 'of.days' et 'of.months' qui contiennent les jours de la semaine et les mois de l'année
* Ajout du type de champ odoo Biginteger
* Ajout de différents fonctions utilitaires : 
   - get_selection_label : Retourne le label d'une valeur d'une selection
   - ceil_to_multiple : Arrondi au multiple supérieur
   - distance_between_points : Calcul la distance entre deux points
   - format_date : Formate une date
   - intervals_overlap : Vérifie si deux intervalles se chevauchent
   - hours_to_strs : Converti une heure en chaine de caractères
   - float_2_hours_minutes : Converti un float sous la forme d'un tuple heure et minutes
   - hours_minutes_2_float : Converti les heures et minutes passées en argument en float
   - compare_date : Compare deux dates avec en paramètre date1, date2, operateur (>, <, >=, <=, ==, !=), par défaut l'opérateur est ==
   - sanitize_text : Supprime les caractères spéciaux non-ascii d'une chaine de caractères (ex: é => e), si non remplacaçable le caractère est supprimé
   - is_valid_url : Vérifie si une chaine de caractères est une url valide