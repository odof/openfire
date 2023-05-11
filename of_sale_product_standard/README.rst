========================
OF Sale Product Standard
========================

Normes des produits vendus
==========================

- Création de l'objet 'Norme' et des vues associées
- Ajout dans les produits de champs "Norme" et "Description de la norme"
- Si un article dispose d'une description de norme, celle-ci sera reporée dans les lignes de devis
  à condition que la norme de l'article soit active et ait l'option "Afficher en impression".

Objet Norme
-----------

Cet objet contient 4 champs:

- Code (code): le code de la norme
- Libellé (name): une brève description de la norme
- Description (description): une description détaillée de la norme
- Afficher en impression (display_docs): cocher cette case pour ajouter la description de la norme
  dans les devis et factures

Il est possible d'archiver une norme.

La description d'une norme est copiée dans l'article quand elle lui est associée.
Elle peut ensuite être personnalisée article par article.

Quand la description d'une norme est modifiée, la description de norme des articles associés est mise à jour à
condition qu'elle n'ait pas été personnalisée.
