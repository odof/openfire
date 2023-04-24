==============
OF sale margin
==============

Module de gestion des marges pour OpenFire.


Fonctionnalités
################

* Mise en place d'un **taux de marge minimum recommandé** par catégorie de produit
    - ce taux de marge sera utilisé pour **contrôler la marge lors de la validation d'une commande** si un article principal est présent dans la commande;
    - si le **taux** de marge de la commande est **inférieur** au **taux de marge spécifié sur la catégorie** associée à l'article principal, un message d'alerte est affiché et la **commande ne peut pas être validée**;
    - le contôle est **appliqué** pour les utilisateurs qui ne sont **pas dans le groupe "Ventes > Administrateur"**.

* Ajout du prix d'achat (`of_seller_price`) du produit sur dans la vue formulaire des lignes de commandes de ventes
    - ce prix est **affiché** pour les utilisateurs qui sont dans le groupe **"OF Marge > Responsable"**.
    - la valeur est également **cachée** quand la commande est en mode **"Vue client"**.

* Modification de **l'affichage du coût** (`purchase_price`) dans les lignes de commandes de ventes
    - le coût est **caché** pour les **utilisateurs standards**;
    - la valeur est également **cachée** quand la commande est en mode **"Vue client"**.
    - le coût est **non modifiable** pour les utilisateurs qui **ne sont pas dans le groupe "OF Marge > (OF) Modifier le coût dans les lignes de ventes"**.

* Modification de **l'affichage** de la vue **formulaire du produit**
    - **toutes les informations liées à la marge** et à son calcul sont **cachées pour les utilisateurs standards** et qui ne sont **pas dans le groupe "OF Marge > Responsable"**.

* Modification de **l'affichage de la marge** (montant et pourcentage) dans la commande de vente
    - la marge est **cachée pour les utilisateurs standards** et qui ne sont **pas dans le groupe "OF Marge > Responsable"**;
    - les valeurs sont également **cachées** quand la commande est en mode **"Vue client"**.



Droits utilisateurs
###################

* Ajout d'une catégorie de droit **"OF Marge"**

* Ajout d'un groupe **"Responsable"** dans cette catégorie **"OF Marge"**

* Ajout d'un groupe **"(OF) Modifier le coût dans les lignes de ventes"**
    - ce groupe est automatiquement ajouté aux utilisateurs du groupe "Ventes > Responsable" et "Ventes > Administrateur"


Paramètres de configuration
###########################

* Ajout d'un paramètre pour activer le contôle de marge lors de la validation d'une commande
