========================
OF Sale Price Management
========================


Module OpenFire pour la gestion des prix et des remises sur les commandes clients
---------------------------------------------------------------------------------

Mise en place d'un wizard permettant de modifier les prix de vente et les remises sur les lignes de commande client.

Ce wizard permet l'application d'une remise globale sur les articles, ainsi que le choix d'un prix TTC.

Il permet également de remettre les articles au prix de vente standard

Il permet également la visualisation de la marge commerciale ligne par ligne

Pour infortion dans le cadre de la remise globale, on autorise l'utilisateur à choisir le total TTC de sa commande.
Afin de permettre ce tour de force (tous les montants TTC ne sont pas atteignables), on augmente la précision du
prix de vente stocké en base de données.

Odoo conserve l'arrondi défini dans l'objet 'decimal.precision' pour l'affichage, mais utilise la pleine précision
pour les calculs des montants TTC.
