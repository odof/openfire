Branche publique du produit Openfire 16.

[[_TOC_]]

# Requirements
La version de python requise est **>= Python 3.9**
<br />


## Modules

La branche Openfire 16 dépend de certains modules OCA


| Nom du module | Repository OCA | Repository ODOF |
|---   |---   |---   |
| base_multi_image <br>base_view_inheritance_extension | https://github.com/OCA/server-tools | https://github.com/odof/server-tools.git |
| web_chatter_position | https://github.com/OCA/web | - |
| remove_odoo_enterprise | https://github.com/OCA/server-brand | - |
| product_multi_image | https://github.com/OCA/product-attribute | https://github.com/odof/product-attribute.git |
| base_location_geonames_import | https://github.com/OCA/partner-contact | - |
| base_location | https://github.com/OCA/partner-contact | - |
| l10n_fr_fec | https://github.com/OCA/l10n-france/ | - |
| sale_product_pack | https://github.com/OCA/product-pack | - |
| sale_comment_template | https://github.com/OCA/sale-reporting | - |

<br />

## Librairies
<br />

Certains modules nécessitent l'installation de librairies python

```
pip3 install -r openfire-requirements.txt
```
<br />

# Code et qualité
<br />

## Linters

Les linters sont des outils qui permettent de vérifier la qualité du code et de le formatter automatiquement.

Voici les linters utilisés dans ce projet :
  - [Flake8](https://flake8.pycqa.org/en/latest/) : vérifie la qualité du code python
  - [Isort](https://pycqa.github.io/isort/) : vérifie l'ordre des imports
  - [Black](https://black.readthedocs.io/en/stable/) : formate le code python
  - [Bandit](https://bandit.readthedocs.io/en/latest/) : vérifie la sécurité du code python
  - [EsLint](https://eslint.org/) : vérifie la qualité du code javascript
  - [Prettier](https://prettier.io/) : formate le code javascript

Les linters sont configurés dans les fichiers suivants :
* [.isort.cfg](.isort.cfg) : configuration d'isort
* [.flake8](.flake8) : configuration de flake8
* [.pre-commit-config.yaml](.pre-commit-config.yaml) : configuration de pre-commit
* [.eslintrc.yml](.eslintrc.yml) : configuration d'eslint
* [.prettierrc.yml](.prettierrc.yml) : configuration de prettier


## Configuration de l'IDE

Un fichier .editorconfig est présent à la racine du projet.
Il permet de configurer l'IDE pour qu'il respecte les règles de qualité du projet.
La plus part des IDE supportent ce fichier de configuration de façon native mais il est possible d'installer un plugin pour les IDE qui ne le supportent pas.


## Gitlab-ci

Gitlab lancera le pipeline de contrôle suivant :
* Isort (configuration dans le fichier [.isort.cfg](.isort.cfg))
* Flake8 (configuration dans le fichier [.flake8](.flake8))
* Black avec les paramètres suivants :
    - --skip-string-normalization
    - --line-length 120
    - --force-exclude="\_\_manifest\_\_\.py"

<br />

## Hook de pre-commit

Vous devez installer les hooks pour vous assurer de commit en respectant les règles de qualité qui seront appliquées via le pipeline Gitlab.

Une inspection Bandit sera également effectué lors du commit.
<br />

### Installation de "pre-commit"


La Librairie [pre-commit](https://pre-commit.com/) facilite l'installation de hooks.

Un fichier Yaml [.pre-commit-config.yaml](.pre-commit-config.yaml) est défini dans le repository avec les hooks à utiliser

Chaque développeur obtiendra les hooks en appelant une simple commande.

Pas besoin d'installer flake8, black ou isort les bonnes versions sont gérées par
[pre-commit](https://pre-commit.com/).

Pour installer les hooks sur ce projet, il suffit de lancer les commandes suivantes dans votre dépôt git :

```
pre-commit install
```
<br />

### Ignorer les erreurs Flake8

Dans le cas où une erreur ne peut vraiment pas être corrigée, vous pouvez désactiver la vérification sur une seule ligne avec `# noqa`.

Il est également possible de spécifier quelle erreur on souhaite désactiver en précisant son code, par exemple : `# noqa: E731`

Voir [documentation Flake8](https://flake8.pycqa.org/en/3.1.1/user/ignoring-errors.html#in-line-ignoring-errors) pour plus d'informations.

<br />

### Ignorer les erreurs Black

Il est possible de demander à Black de ne pas reformater un bloc de code ou une ligne spécifiquement :
* bloc de code
```python
# fmt: off
foo = [
    1,
    2,
    3
]
# fmt: on
```
Il faut bien penser à réactiver le reformatage Black après le bloc

* ligne de code
```python
foo = 1  # fmt: skip
```

Voir [documentation Black](https://black.readthedocs.io/en/stable/the_black_code_style/current_style.html#code-style) pour plus d'informations.

<br />

### Ignorer les erreurs Bandit

Bandit peut également remonter des alerte de sécurités que vous souhaitez ignorer.

Vous souhaitez l'ignorer soit car  vous avez consience de cette alerte et elle est maitrisée ou soit vous souhaitez tout simplement passez outre l'alerte de par son niveau de criticité

Ignorer tout alerte :

```python
self.process = subprocess.Popen('/bin/echo', shell=True)  # nosec
```
<br />
Ignorer un ou plusieurs code alerte précisémment :

```python
self.process = subprocess.Popen('/bin/ls *', shell=True)  # nosec B602, B607
```

<br />

### Désactiver pre-commit au commit


**Ce n'est pas recommandé**, mais parfois, vous devez contourner les hooks de pre-commit.

Pour forcer le commit sans vérifier les hooks, ajoutez l'option `-n` ou `--no-verify`
dans la ligne de commande :

```
git commit some-file-with-pep8-black-errors.py -m "Dirty commit" -n
```
<br />

# Ressources

Documentations :

- [pre-commit](https://pre-commit.com/)

- [Flake8](https://flake8.pycqa.org/en/latest/)

- [Isort](https://pycqa.github.io/isort/)

- [Black](https://black.readthedocs.io/en/stable/)

- [Bandit](https://bandit.readthedocs.io/en/latest/)

- [EsLint](https://eslint.org/)

- [Prettier](https://prettier.io/)

- [EditorConfig](https://editorconfig.org/)
