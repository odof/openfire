========================
OF sale comment template
========================

Module d'extension du module OCA `sale_comment_template` afin de modifier son fonctionnement pour correspondre à nos besoins.


Fonctionnalités
################

* **Modification** de la valeur par défaut du champs **"Moteur"** pour le mettre à **"qweb"** et mettre le **champ en readonly**

* Le champ **"Domaine"** est maintenant par **défaut invisible** (il est affiché en mode développeur)

* Ajouter la société par défaut dans le champ 'company_id'

* Le champ **"Modèles"** est maintenant un champ sélection, les valeurs possibles sont "Bon de commande" et "Facture"


Paramètres de configuration
###########################


* Ajout d'un paramètre de configuration pour la **propagation des commentaires de devis à facture**
    - cf **"Configuration > Paramètres > Ventes > Devis & Commandes > Propagation des commentaires"**
    - Les valeurs possibles sont:
        - Ne pas garder les commentaires
        - Garder les commentaires (tous les commentaires seront propagés vers la facture)
        - Garder que les commentaires du haut
        - Garder que les commentaires du bas
