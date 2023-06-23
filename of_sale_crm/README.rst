===========
OF Sale crm
===========


Module OpenFire de lien CRM - ventes
------------------------------------
- Modification automatique de la date d'une activité en fonction des dates du bon de commande
- Création automatique d'activité à la création d'un devis
- Possibilité de verrouiller la confirmation d'un devis si des activités sont à réaliser
- Ajout d'un champ "Prospecteur" dans les devis/commandes et factures
- Ajout notion de 'client confirmé': un client confirmé est un client qui a au moins une vente confirmée ou une facture validée. Les autres sont des prospects.

A déplacer dans of_sale (ou autre ?):
-------------------------------------
- Modification de l'état des bons de commande : devis/devis envoyé -> estimation/devis
- Ajout des objectifs de vente mensuels
- changement méthode de calcul du nombre de ventes client -> ne prend plus en compte que les ventes confirmées (et non les devis)
