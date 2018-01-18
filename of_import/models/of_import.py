# -*- coding: utf-8 -*-

import csv
import datetime
import io
import itertools
import logging
import time
import base64

from odoo import api, fields, models
from odoo.tools.translate import _
from odoo.tools.safe_eval import safe_eval
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

try:
    import xlrd
    try:
        from xlrd import xlsx
    except ImportError:
        xlsx = None
except ImportError:
    xlrd = xlsx = None

try:
    from odoo.addons.base_import.models import odf_ods_reader
except ImportError:
    odf_ods_reader = None

try:
    import chardet
except ImportError:
    chardet = None

_logger = logging.getLogger(__name__)

EXTENSIONS = ('csv', 'xls', 'xlsx', 'ods')
SELECT_EXTENSIONS = [
    ('csv', 'CSV'),
    ('xls', 'MS-Excel'),
    ('xlsx', 'MS-Excel-10'),
    ('ods', 'LibreOffice'),
    ]

CODE_IMPORT_ERREUR = -1
CODE_IMPORT_CREATION = 0
CODE_IMPORT_MODIFICATION = 1

class OfImportError(Exception):
    def __init__(self, msg):
        self.msg = msg

class OfImportProductConfigTemplate(models.AbstractModel):
    _name = 'of.import.product.config.template'
    _description = u"Classe regroupant les paramètres personnalisables dans la configuration d'import de tarifs"

    of_import_price = fields.Char(string='Prix de vente HT',
                                  help=u"""Modification à appliquer sur le prix public hors taxe pour calculer le prix de vente.

Exemples :
 ppht : Conserve le prix de vente conseillé (prix public hors taxe)
 ppht * 1.05 + 10 : Augmente le prix de vente de 5%, plus 10€""")
    of_import_remise = fields.Char(string="Remise",
                                   help=u"""Remise à appliquer sur les articles de ce fournisseur.
La remise est appliquée sur le prix public pour calculer le prix d'achat.

Exemples :
 rc : Utiliser la remise conseillée
 40 : Forcer une remise de 40%
 cumul(10,5) : Appliquer la remise conseillée, puis une remise de 10%, puis une remise de 5%
 cumul(14.5) : Équivalent à la ligne précedente, une remise de 10% puis 5% fait 14.5% au total
""")
    of_import_cout = fields.Char(string='Prix de revient',
                                 help=u"""Permet le calcul du prix de revient en fonction du prix d'achat

Exemples :
 pa : Conserve le prix d'achat calculé à partir du prix des formules du prix de vente et de la remise
 pa * 1.05 + 20 : Prix d'achat augmenté de 5% puis augmenté de 20€
""")
    of_import_categ_id = fields.Many2one('product.category', string=u"Catégorie")

    @api.model
    def get_config_field_list(self):
        return [
            'of_import_price',
            'of_import_remise',
            'of_import_cout',
            'of_import_categ_id',
        ]

class OfImportProductCategConfig(models.Model):
    _name = 'of.import.product.categ.config'
    _inherit = 'of.import.product.config.template'
    _order = 'categ_origin'

    brand_id = fields.Many2one('of.product.brand', required=True)
    categ_origin = fields.Char(string=u"Catégorie d'origine", required=True)

    _sql_constraints = [
        ('categ_origin_uniq', 'unique(brand_id, categ_origin)', u"Une catégorie de produits ne peut être renseignée qu'une fois"),
    ]

class OFProductBrand(models.Model):
    _name = 'of.product.brand'
    _inherit = ('of.product.brand', 'of.import.product.config.template')

    categ_ids = fields.One2many('of.import.product.categ.config', 'brand_id', string="Catégories")
    product_config_ids = fields.One2many('product.template', string="Articles", compute="_compute_product_config_ids",
                                         inverse="_inverse_product_config_ids", domain="[('brand_id', '=', id)]")

    of_import_price = fields.Char(required=True, default='ppht')
    of_import_remise = fields.Char(required=True)
    of_import_cout = fields.Char(required=True, default="pa")
    of_import_categ_id = fields.Many2one(required=True)


    @api.depends('product_ids.of_import_price', 'product_ids.of_import_remise', 'product_ids.of_import_categ_id')  # , 'product_ids.of_import_price_extra'
    def _compute_product_config_ids(self):
        product_obj = self.env['product.template']
        fields = self.get_config_field_list()
        domain = ['|'] * (len(fields) - 1) + [(field, '!=', False) for field in fields]
        for brand in self:
            brand.product_config_ids = product_obj.search([('brand_id', '=', self.id)] + domain)

    @api.multi
    def _inverse_product_config_ids(self):
        product_obj = self.env['product.template']
        fields = self.get_config_field_list()
        deleted = product_obj.browse()
        for brand in self:
            for line in brand.product_config_ids:
                if line[0] == 4:
                    # pas de modification
                    pass
                if line[0] in (2, 3):
                    # Suppression de ligne = annulation des règles de calcul
                    deleted |= line[1]
                if line[0] == 1:
                    # Ajout ou modification d'une ligne = définition des ègles de calcul
                    product_obj.browse(line[1]).write({field: line[2][field] for field in fields if field in line[2]})
                if line[0] == 0:
                    # Qui irait créer un article depuis cet endroit?
                    pass
        if deleted:
            deleted.write(dict.fromkeys(fields, False))

    @api.model
    def compute_remise(self, *remises):
        result = 100
        for remise in remises:
            result *= (100 - remise) / 100.0
        return 100 - result

    @api.multi
    def compute_product_categ(self, categ_name, product=None):
        self.ensure_one()

        # Configuration de la catégorie au niveau de l'article
        if product and product.of_import_categ_id:
            return product.of_import_categ_id

        # Configuration de la catégorie dans la marque pour ce nom de catégorie fournisseur
        categ_config = self.env['of.import.product.categ.config'].search([('brand_id', '=', self.id), ('categ_origin', '=', categ_name)])
        if categ_config and categ_config.of_import_categ_id:
            return categ_config.of_import_categ_id

        # Vérification si la catégorie par défaut pour cette marque correspond au nom de catégorie fourni
        if self.of_import_categ_id.name == categ_name:
            return self.of_import_categ_id

        # Si une catégorie existante porte le même nom que la catégorie fournisseur, on l'utilise
        categ = self.env['product.category'].search([('name', '=', categ_name)])
        if categ:
            if len(categ) == 1:
                return categ
            else:
                # Plusieurs catégories existantes correspondent, on ne sait pas laquelle choisir
                #  et la catégorie par défaut pour la marque ne correspond pas

                # @todo: Faut-il utiliser la marque par défaut quand-même?
                # Note: le return False provoque un recalcul dans l'import d'article, qui génère un message
                #   d'erreur adapté à la détection de plusieurs valeurs pour un many2one
                return False

        # Enfin, dernière solution, retour de la catégorie par défaut pour la marque
        return self.of_import_categ_id

    @api.multi
    def compute_product_price(self, list_price, categ_name, product=None):
        """
        @param categ_name: Nom de la catégorie de produit telle que donnée par le fournisseur
        @param product: objet product.template si existant sur la base actuellement
        """
        self.ensure_one()

        categ_config = self.env['of.import.product.categ.config'].search([('brand_id', '=', self.id), ('categ_origin', '=', categ_name)])

        eval_dict = {
            'ppht' : list_price,
            'cumul': self.compute_remise,
        }

        fields = (('of_import_price', 'list_price', 'le prix public ht'),
                  ('of_import_remise', 'remise', 'la remise'),
                  ('of_import_cout', 'standard_price', u'le coût'))
        values = {}
        for config_field, product_field, text in fields:
            for obj in (product, categ_config, self):
                if obj and obj[config_field]:
                    value = safe_eval(obj[config_field], eval_dict)
                    if product_field == 'remise':
                        # Une fois la remise calculée, on peut ajouter le prix d'achat au eval_dict pour le calcul du coût final
                        eval_dict['pa'] = values['list_price'] * (100.0 - value) / 100.0
                    else:
                        values[product_field] = value
                    break
            else:
                # Aucune formule n'a été renseignée. Cette formule n'est pas obligatoire pour le coût
                if product_field != 'standard_price':
                    raise OfImportError(u"Aucune formule n'est renseignée pour %s de cet article." % (text, ))

        values['of_seller_price'] = eval_dict['pa']
        return values

    @api.multi
    def compute_product_values(self, list_price, categ_name, product=None):
        self.ensure_one()

        categ = self.compute_product_categ(categ_name, product=product)
        if not categ:
            raise UserError(u"Impossible de trouver la catégorie de produits correspondant à \"%s\"" % (categ_name, ))

        values = self.compute_product_price(list_price, categ_name, product=product)
        values['categ_id'] = categ.id
        return values

    @api.multi
    def action_update_products(self):
        """
        Recalcule les champs de l'article en fonction de la configuration de la marque
        et des paramètres d'import de l'article (dans product_supplierinfo)
        """
        # On prétend venir d'un import afin de lancer la propagation du coût sur les différentes sociétés
        self = self.with_context(from_import=True)
        for brand in self:
            supplier = brand.partner_id
            for product in brand.product_ids:
                for seller in product.seller_ids:
                    if seller.name == supplier:
                        values = self.compute_product_values(seller.pp_ht,
                                                             seller.of_product_category_name,
                                                             product)
                        values = {key: val for key, val in values.iteritems() if product[key] != val}
                        if values:
                            product.write(values)
                        break

class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = ('product.template', 'of.import.product.config.template')

class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    def of_propage_cout(self, cout):
        # Le coût (standard_price) est défini sur l'ensemble des sociétés.
        # Si le module of_base_multicompany est installé, il est inutile de le diffuser sur les sociétés "magasins"
        companies = self.env['res.company'].search(['|', ('chart_template_id', '!=', False), ('parent_id', '=', False)])
        property_obj = self.env['ir.property'].sudo()
        values = {product.id: cout for product in self}
        for company in companies:
            property_obj.with_context(force_company=company.id).set_multi('standard_price', 'product.product', values)

    @api.model
    def create(self, vals):
        propage_cout = self._context.get('from_import') and 'standard_price' in vals
        if propage_cout:
            cout = vals.pop('standard_price')
        product = super(ProductProduct, self).create(vals)
        if propage_cout:
            product.of_propage_cout(cout)
        return product

    @api.multi
    def write(self, vals):
        propage_cout = self._context.get('from_import') and 'standard_price' in vals
        if propage_cout:
            cout = vals.pop('standard_price')
        super(ProductProduct, self).write(vals)
        if propage_cout:
            self.of_propage_cout(cout)
        return True

class OfImport(models.Model):
    _name = 'of.import'

    user_id = fields.Many2one('res.users', u'Utilisateur', readonly=True, default=lambda self: self._uid)

    name = fields.Char(u'Nom', size=64, required=True)
    type_import = fields.Selection([('product.template', u'Articles'), ('res.partner', u'Partenaires'), ('crm.lead', u'Pistes/opportunités'), ('res.partner.bank', u'Comptes en banques partenaire'), ('of.service', u'Services OpenFire')], string=u"Type d'import", required=True)

    date = fields.Datetime('Date', required=True, default=lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'), help=u"Date qui sera affectée aux imports comme date de valeur.")
    date_debut_import = fields.Datetime(u'Début', readonly=True)
    date_fin_import = fields.Datetime(u'Fin', readonly=True)
    time_lapse = fields.Char(string=u'Importé en', compute="_compute_time_lapse")

    file = fields.Binary(u'Fichier', required=True)
    file_name = fields.Char(u'Nom du fichier')
    file_type = fields.Selection(SELECT_EXTENSIONS, u'Type de fichier', compute="_compute_file_type")
    file_size = fields.Char(u'Taille du fichier', compute="_compute_file_size")
    file_encoding = fields.Char(u'Encodage')

    separateur = fields.Char(u'Séparateur champs', help=u"Caractère séparateur des champs dans le fichier d'import.\nSi non renseigné, le système essaye de le déterminer lui même.\nMettre \\t pour tabulation.")

    prefixe = fields.Char(u'Préfixe référence', size=10, help=u"Texte qui précèdera la référence.")

    state = fields.Selection([('brouillon', u'Brouillon'), ('importe', u'Importé'), ('annule', u'Annulé')], u'État', default='brouillon', readonly=True)

    nb_total = fields.Integer(u'Nombre total', readonly=True)
    nb_ajout = fields.Integer(u'Ajoutés', readonly=True)
    nb_maj = fields.Integer(u'Mis à jour', readonly=True)
    nb_echoue = fields.Integer(u'Échoués/ignorés', readonly=True)

    sortie_note = fields.Text(u'Note', compute='_compute_sortie_note', readonly=True)
    sortie_succes = fields.Text(u'Information', readonly=True)
    sortie_avertissement = fields.Text(u'Avertissements', readonly=True)
    sortie_erreur = fields.Text(u'Erreurs', readonly=True)

    @api.depends('file', 'file_name')
    def _compute_file_type(self):
        """Get file type par extension ('csv', 'xls', 'xlsx', 'ods')"""
        for imp in self:
            file_name = self.file_name
            if file_name:
                splitted = file_name.split(".")
                if len(splitted) > 1:
                    extension = splitted[-1]
                    if extension not in EXTENSIONS:
                        raise UserError(u"Type de fichier non reconnu !")
                    imp.file_type = extension
                else:
                    raise UserError(u"Type de fichier non reconnu !")
            else:
                imp.file_type = False

    @api.multi
    def _compute_encoding(self, file_enc):
        try:
            result = chardet.detect(file_enc)
            if result:
                file_encoding = result['encoding']
                return file_encoding
            else:
                raise UserError(u'Encodage non reconnu.')
        except:
            raise UserError(u'Erreur : encodage non reconnu.')

    @api.depends('file')
    def _compute_file_size(self):
        if not self.file:
            self.file_size = "--"
        else:
            if len(self.file) > 20:
                self.file_size = "--"
            else:
                self.file_size = self.file

    @api.depends('date_debut_import', 'date_fin_import')
    def _compute_time_lapse(self):
        if self.date_debut_import:
            start_dt = fields.Datetime.from_string(self.date_debut_import)
            finish_dt = fields.Datetime.from_string(self.date_fin_import)
            self.time_lapse = finish_dt - start_dt
        else:
            self.time_lapse = False

    @api.depends('type_import')
    def _compute_sortie_note(self):
        "Met à jour la liste des champs Odoo disponibles pour l'import dans le champ note"
        for imp in self:
            sortie_note = ''
            for champ, valeur in self.get_champs_odoo(self.type_import).items():
                if champ in ('tz', 'lang'):  # Champs qui plantent lors de l'import, on les ignore.
                    continue
                sortie_note += "- " + valeur['description'] + " : " + champ
                if valeur['type'] == 'selection':
                    sortie_note += u" [ valeurs autorisées : "
                    for cle in self.env[self.type_import]._fields[champ].get_values(self.env):
                        sortie_note += cle + " "
                    sortie_note += ']'
                sortie_note += '\n'

            if sortie_note:
                sortie_note = u"Champs disponibles pour l'import (en-tête de colonne) :\n" + sortie_note
            imp.sortie_note = sortie_note
#### READERS #####
# Un reader retourne au premier appel la liste des champs du fichier (éléments de la première ligne)
# Aux appels suivants, le reader retoune un dictionnaire {nom de la colonne: valeur} pour la ligne suivante

    @api.multi
    def _read_csv(self):
        # Lecture du fichier d'import par la bibliothèque csv de python
        csv_data = base64.decodestring(self.file)
        dialect = csv.Sniffer().sniff(csv_data)   # Deviner automatiquement les paramètres : caractère séparateur, type de saut de ligne,...
        file_encoding = self._compute_encoding(csv_data)
        self.file_encoding = file_encoding

        # Encode en utf-8
        if file_encoding != 'utf-8':
            csv_data = csv_data.decode(file_encoding).encode('utf-8')

        # On prend le séparateur indiqué dans le formulaire si est renseigné.
        # Sinon on prend celui deviné par la bibliothèque csv, et si vierge, on prend le ; par défaut.
        if self.separateur and self.separateur.strip(' '):
            dialect.delimiter = str(self.separateur.strip(' ').replace('\\t', '\t'))
        else:
            if dialect.delimiter and dialect.delimiter.strip(' '):
                self.separateur = dialect.delimiter.replace('\t', '\\t')
            else:
                self.separateur = dialect.delimiter = ';'

        reader = csv.DictReader(
            StringIO(csv_data),
            dialect=dialect)

        prems = True
        for row in reader:
            if prems:
                prems = False
                yield [item.strip().decode('utf8', 'ignore') for item in row]
            if not any(x for x in row if x.strip()):
                # Ligne vide
                continue
            yield {key.strip().decode('utf8', 'ignore'): value.strip().decode('utf8', 'ignore')
                   for key, value in row.iteritems()}

    ## OPENOFFICE ##
    @api.multi
    def _read_ods(self):
        raise UserError(u"Pour l'instant, il n'est pas possible d'importer des fichiers OpenOffice.")

        """ Read file content using ODSReader custom lib """
        doc = odf_ods_reader.ODSReader(file=io.BytesIO(self.file))

        return (
            row
            for row in doc.getFirstSheet()
            if any(x for x in row if x.strip())
            )

    ## MS OFFICE ##
    @api.multi
    def _read_xls(self):
        """ Read file content, using xlrd lib """
        book = xlrd.open_workbook(file_contents=base64.b64decode(self.file))
        sheet = book.sheet_by_index(0)
        header = False
        # emulate Sheet.get_rows for pre-0.9.4
        for row in itertools.imap(sheet.row, range(sheet.nrows)):
            values = []
            for cell in row:
                if cell.ctype is xlrd.XL_CELL_NUMBER:
                    is_float = cell.value % 1 != 0.0
                    values.append(
                        unicode(cell.value)
                        if is_float
                        else unicode(int(cell.value))
                    )
                elif cell.ctype is xlrd.XL_CELL_DATE:
                    is_datetime = cell.value % 1 != 0.0
                    # emulate xldate_as_datetime for pre-0.9.3
                    dt = datetime.datetime(*xlrd.xldate.xldate_as_tuple(cell.value, book.datemode))
                    values.append(
                        dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                        if is_datetime
                        else dt.strftime(DEFAULT_SERVER_DATE_FORMAT)
                    )
                elif cell.ctype is xlrd.XL_CELL_BOOLEAN:
                    values.append(u'True' if cell.value else u'False')
                elif cell.ctype is xlrd.XL_CELL_ERROR:
                    raise ValueError(
                        _("Error cell found while reading XLS/XLSX file: %s") %
                        xlrd.error_text_from_code.get(
                            cell.value, "unknown error code %s" % cell.value)
                    )
                else:
                    values.append(cell.value.strip())
            if any(values):
                if header:
                    yield {header[i]: values[i] for i in range(len(header))}
                else:
                    header = values
                    yield values

    def get_champs_odoo(self, model=''):
        "Renvoie un dictionnaire contenant les caractéristiques des champs Odoo en fonction du type d'import sélectionné (champ type_import)"

        if not model:
            return {}

        champs_odoo = {}

        # On récupère la liste des champs de l'objet depuis ir.model.fields
        obj = self.env['ir.model.fields'].search([('model', '=', model)])
        for champ in obj:
            champs_odoo[champ.name] = {
                'description': champ.field_description,
                'requis': champ.required,
                'type': champ.ttype,
                'relation': champ.relation,
                'relation_champ': champ.relation_field}

        # Des champs qui sont obligatoires peuvent avoir une valeur par défaut (donc in fine pas d'obligation de les renseigner).
        # On récupère les champs qui ont une valeur par défaut et on indique qu'ils ne sont pas obligatoires.
        champs_requis = [key for key, vals in champs_odoo.iteritems() if vals['requis']]
        for i in self.env[model].default_get(champs_requis):
            champs_odoo[i]['requis'] = False

        # On ne rend pas obligatoire manuellement un champ qui est marqué comme obligatoire car créé par la fonction create d'Odoo.
        if model == 'product.template':
            if 'product_variant_ids' in champs_odoo:
                champs_odoo['product_variant_ids']['requis'] = False

            if 'brand_id' in champs_odoo:
                # Dans le cadre de l'import de tarif, on rend obligatoire le renseignement de la marque de l'article
                champs_odoo['brand_id']['requis'] = True

        return champs_odoo

    @api.multi
    def bouton_remettre_brouillon(self):
        for imp in self:
            imp.state = 'brouillon'
        return True

    @api.multi
    def bouton_simuler(self):
        self.importer(simuler=True)
        return True

    @api.multi
    def bouton_importer(self):
        self.importer(simuler=False)
        return True

    def _choisir_reader(self):
        """Choisir reader selon extension"""
        if self.file:
            # OPENOFFICE
            if self.file_type == 'ods':
                return self._read_ods()

            # MS-OFFICE
            elif self.file_type == 'xls' or self.file_type == 'xlsx':
                return self._read_xls()

            # CSV
            elif self.file_type == 'csv':
                return self._read_csv()

            # Error
            else:
                raise UserError(u'Type de fichier non reconnu')

### IMPORT ###

    @api.multi
    def _pre_calcule_ligne(self, champs_fichier, ligne, model_data):
        """
        @return: Dictionnaire de valeurs pour l'import
        """
        res = {}
        for key, val in model_data.iteritems():
            if key.startswith('default_'):
                res[key[8:]] = val
        return res

    @api.multi
    def _post_calcule_ligne(self, champs_fichier, ligne, model_data, res_objet, valeurs):
        """
        @param valeurs: Dictionnaire de valeurs pour l'import sur lequel cette fonction appliquera des modifications
        """
        if self.type_import == 'product.template':
            brand_id = valeurs.get('brand_id')
            if brand_id:
                brand = self.env['of.product.brand'].browse(brand_id)
            else:
                brand = res_objet and res_objet.brand_id
                # Si brand n'est pas défini, une exception sera automatiquement générée plus tard
                # car la marque est un champ obligatoire pour l'import de tarif

            # Calcul des prix d'achat/vente en fonction des règles de calcul et du prix public ht
            if 'list_price' in valeurs and brand:
                valeurs['of_seller_pp_ht'] = valeurs['list_price']
                valeurs.update(brand.compute_product_price(valeurs['list_price'], valeurs.get('of_seller_product_category_name', res_objet and res_objet.of_seller_product_category_name or ''), res_objet))

    @api.multi
    def _importer_ligne(self, ligne, champs_fichier, champs_odoo, i, model_data, doublons, simuler):
        """
        Cas de l'import d'articles :
        Lors de l'import d'articles, la marque est un élément obligatoire qui peut être déduit du préfixe d'import ou
            calculé ligne par ligne dans une colonne dédiée du fichier importé.
        Le calcul de la marque doit être réalisé avant toute chose.
        En effet, il conditionne le préfixe ajouté à la référence de l'article, laquelle permet d'identifier un article déjà
            existant en DB, lequel pouvant définir des paramètres d'import pour forcer la catégorie de produit.


        L'ordre logique du processus d'import est donc
        1 - Détection de la marque
        2 - Mise à jour de la référence de l'article avec le préfixe de la marque (si non déjà inclus, par exemple avec export+import)
        3 - Détection d'article existant, impliquant une mise à jour et non une création de nouvel article
        4 - Import des éléments du fichier

        L'import de la catégorie de produit ne se fait pas dans _post_calcule_ligne() car il s'agit d'un champ one2many,
            on s'évite de recopier le processus de lecture de ce champ ainsi que la fonction erreur()
            ce qui facilitera les mises à jour futures

        """
        erreur_msg = [""]

        def erreur(msg):
            """
            Gestion des erreurs
            En mode simulation, toutes les anomalies sont listées pour chaque ligne d'import.
            En mode import, chaque ligne est abandonnée à la première anomalie rencontrée.
            """
            erreur_msg[0] += msg
            if not simuler:
                raise OfImportError(erreur_msg[0])
        model = self.type_import
        model_obj = self.env[model_data['model']].with_context(from_import=True)

        # res_objet correspond à l'élément déjà existant en base de données, le cas échéant
        # cette variable sera renseignée à l'import du champ primaire de l'objet
        res_objet = model_obj

        libelle_ref = u"réf. " + ligne.get(model_data['champ_reference'] or model_data['champ_primaire'] or 'name', '')

        # PARCOURS DE TOUS LES CHAMPS DE L'ENREGISTREMENT
        valeurs = self._pre_calcule_ligne(champs_fichier, ligne, model_data)  # Champs à importer (pour envoi à fonction create ou write)

        # Parcours de tous les champs de la ligne
        for champ_fichier in champs_fichier:

            # Pour import articles, champ price est le coût d'achat à mettre dans le prix fournisseur.
            # On l'ignore car sera récupéré avec le champ seller_ids (fournisseur), voir plus bas.
            # Note : Normalement, le prix d'achat ne devrait pas être importé.
            #        Le seul champ importé devrait être le prix public hors taxe.
            #        Le prix d'achat devrait être calculé automatiquement avec la remise configurée côté client.
            if model == 'product.template' and champ_fichier == 'price':
                continue

            # Si le nom du champ contient un champ relation c'est à dire se terminant par /nom_du_champ on l'enlève.
            champ_fichier_sansrel = champ_fichier[0:champ_fichier.rfind('/') if champ_fichier.rfind('/') != -1 else len(champ_fichier)].strip()

            if champ_fichier_sansrel in champs_odoo:  # On ne récupère que les champs du fichier d'import qui sont des champs de l'objet (on ignore les champs inconnus du fichier d'import).
                ligne[champ_fichier] = ligne[champ_fichier]

                if ligne[champ_fichier].lower() == "#vide":
                    ligne[champ_fichier] = "#vide"

    #
    # VÉRIFICATION DE L'INTÉGRITÉ DE LA VALEUR DES CHAMPS
    # POUR LES CRITÈRES QUI NE DÉPENDENT PAS DU TYPE DU CHAMP
    #

                # si le champs est requis, vérification qu'il est renseigné
                if champs_odoo[champ_fichier_sansrel]['requis'] and (ligne[champ_fichier] == "#vide" or (ligne[champ_fichier] == "" and not valeurs.get(champ_fichier_sansrel))):
                    erreur(u"Ligne %s : champ %s (%s) vide alors que requis. %s non importé.\n" % (i, champs_odoo[champ_fichier_sansrel]['description'], champ_fichier, model_data['nom_objet'].capitalize()))

                # Si le champ relation est un id, vérification qu'est un entier
                if champs_odoo[champ_fichier_sansrel]['relation_champ'] == 'id':
                    try:
                        int(ligne[champ_fichier])
                    except ValueError:
                        erreur(u"Ligne %s : champ %s (%s) n'est pas un id (nombre entier) alors que le champ relation (après le /) est un id. %s non importé.\n" % (i,  champs_odoo[champ_fichier_sansrel]['description'], champ_fichier, model_data['nom_objet'].capitalize()))

    #
    # FORMATAGE ET VÉRIFICATION DE L'INTÉGRITÉ DE LA VALEUR DES CHAMPS
    # POUR LES CRITÈRES QUI DÉPENDENT DU TYPE DU CHAMP
    #

                # Si est un float
                if champs_odoo[champ_fichier_sansrel]['type'] == 'float':
                    ligne[champ_fichier] = ligne[champ_fichier].replace(',', '.')
                    if ligne[champ_fichier] != "":
                        try:
                            valeurs[champ_fichier_sansrel] = float(ligne[champ_fichier])
                        except ValueError:
                            erreur(u"Ligne %s : champ %s (%s) n'est pas un nombre. %s non importé.\n" % (i, champs_odoo[champ_fichier_sansrel]['description'], champ_fichier_sansrel, model_data['nom_objet'].capitalize()))

                # Si est un field selection
                elif champs_odoo[champ_fichier_sansrel]['type'] == 'selection':
                    # C'est un champ sélection. On vérifie que les données sont autorisées.
                    if ligne[champ_fichier] not in dict(self.env[model]._fields[champ_fichier].selection):
                        erreur(u"Ligne %s : champ %s (%s) valeur \"%s\" non autorisée. %s non importé.\n" % (i, champs_odoo[champ_fichier_sansrel]['description'], champ_fichier, ligne[champ_fichier], model_data['nom_objet'].capitalize()))
                    else:
                        valeurs[champ_fichier_sansrel] = ligne[champ_fichier]

                # Si est un boolean
                elif champs_odoo[champ_fichier_sansrel]['type'] == 'boolean':
                    if ligne[champ_fichier].upper() in ('1', "TRUE", "VRAI"):
                        valeurs[champ_fichier] = True
                    elif ligne[champ_fichier].upper() in ('0', "FALSE", "FAUX"):
                        valeurs[champ_fichier] = False
                    else:
                        erreur(u"Ligne %s : champ %s (%s) valeur \"%s\" non autorisée (admis 0, 1, True, False, vrai, faux). %s non importé.\n" % (i, champs_odoo[champ_fichier_sansrel]['description'], champ_fichier, ligne[champ_fichier], model_data['nom_objet'].capitalize()))

                # si est un many2one
                elif champs_odoo[champ_fichier_sansrel]['type'] == 'many2one':
                    if ligne[champ_fichier] == "#vide" and not champs_odoo[champ_fichier_sansrel]['requis']:
                        # Si le champ n'est pas obligatoire et qu'il est vide, on met une valeur vide.
                        valeurs[champ_fichier_sansrel] = ""
                    elif ligne[champ_fichier] != "":
                        recherche = False
                        # Si import partenaires et si c'est le compte comptable client ou fournisseur, on regarde si pointe sur un compte comptable existant
                        if model == 'res.partner' and champ_fichier == 'property_account_receivable_id':
                            res_ids = self.env[champs_odoo[champ_fichier_sansrel]['relation']].with_context(active_test=False).search([('code', '=', ligne[champ_fichier]), ('internal_type', '=', 'receivable')])
                        elif model == 'res.partner' and champ_fichier == 'property_account_payable_id':
                            res_ids = self.env[champs_odoo[champ_fichier_sansrel]['relation']].with_context(active_test=False).search([('code', '=', ligne[champ_fichier]), ('internal_type', '=', 'payable')])
                        # Si import de produit, la catégorie de produit peut avoir une correspondance
                        elif model == 'product.template' and champ_fichier == 'categ_id':
                            # Sauvegarde de la catégorie donnée par le fournisseur
                            valeurs['of_seller_product_category_name'] = ligne[champ_fichier]

                            brand = valeurs.get('brand_id') and self.env['of.product.brand'].browse(valeurs['brand_id'])
                            if res_objet and not brand:
                                brand = res_objet.brand_id

                            categ = brand and brand.compute_product_categ(ligne[champ_fichier], product=res_objet)

                            if categ:
                                res_ids = categ
                            else:
                                recherche = True
                        else:
                            recherche = True

                        if recherche:
                            if ligne[champ_fichier] == "#vide":
                                res_ids = ""
                            else:
                                res_ids = self.env[champs_odoo[champ_fichier_sansrel]['relation']].with_context(active_test=False).search([(champs_odoo[champ_fichier_sansrel]['relation_champ'] or 'name', '=', ligne[champ_fichier])])

                        if len(res_ids) == 1:
                            valeurs[champ_fichier_sansrel] = res_ids.id
                            if model == 'product.template' and champ_fichier_sansrel == 'brand_id':
                                if res_ids.partner_id:  # Le fournisseur est devenu un champ obligatoire de la marque. Cette vérification pourra être retirée.
                                    valeurs['seller_ids'] = [(5, ), (0, 0, {'name': res_ids.partner_id.id})]
                        elif len(res_ids) > 1:
                            erreur(u"Ligne %s : champ %s (%s) valeur \"%s\" a plusieurs correspondances. %s non importé.\n" % (i, champs_odoo[champ_fichier_sansrel]['description'], champ_fichier, ligne[champ_fichier], model_data['nom_objet'].capitalize()))
                        else:
                            # Si import de partenaires et champ compte comptable (client et fournisseur), on le crée.
                            if model == 'res.partner' and champ_fichier == 'property_account_receivable_id' and 'name' in ligne:
                                if not simuler:
                                    valeurs[champ_fichier_sansrel] = self.env[champs_odoo[champ_fichier_sansrel]['relation']].create({'name': ligne['name'], 'code': ligne[champ_fichier], 'reconcile': True, 'user_type_id': model_data['data_account_type_receivable_id']})
                            elif model == 'res.partner' and champ_fichier == 'property_account_payable_id' and 'name' in ligne:
                                if not simuler:
                                    valeurs[champ_fichier_sansrel] = self.env[champs_odoo[champ_fichier_sansrel]['relation']].create({'name': ligne['name'], 'code': ligne[champ_fichier], 'reconcile': True, 'user_type_id': model_data['data_account_type_payable_id']})
                            elif ligne[champ_fichier] == "#vide":
                                valeurs[champ_fichier_sansrel] = ''
                            else:
                                erreur(u"Ligne %s : champ %s (%s) valeur \"%s\" n'a pas de correspondance. %s non importé.\n" % (i, champs_odoo[champ_fichier_sansrel]['description'], champ_fichier, ligne[champ_fichier], model_data['nom_objet'].capitalize()))

                # Si est un one2many
                elif champs_odoo[champ_fichier_sansrel]['type'] == 'one2many':
                    # Cas des fournisseurs pour les produits. Il y a un objet intermédiaire avec un enregistrement pour chaque produit.
                    # On crée le fournisseur dans cet objet en renseignant le prix d'achat
                    if model == 'product.template' and champ_fichier == 'seller_ids' and valeurs.get('brand_id'):
                        if not ligne[champ_fichier]:
                            continue

                        brand = self.env['of.product.brand'].browse(valeurs['brand_id'])
                        if brand.partner_id:
                            if brand.partner_id.name.strip() != ligne[champ_fichier]:
                                erreur(u"Ligne %s : champ %s (%s) Le fournisseur choisi (%s) ne correspond pas à celui de la marque %s (%s). %s non importé.\n" % (i, champs_odoo[champ_fichier_sansrel]['description'], champ_fichier, ligne[champ_fichier], brand.name, brand.partner_id.name, model_data['nom_objet'].capitalize()))
                        else:
                            res_ids = self.env['res.partner'].search([('name', '=', ligne[champ_fichier]), ('supplier', '=', True)])

                            if len(res_ids) == 1:
                                valeurs[champ_fichier_sansrel] = [(5, ), (0, 0, {'name': res_ids.id})]
                            elif len(res_ids) > 1:
                                erreur(u"Ligne %s : champ %s (%s) valeur \"%s\" a plusieurs correspondances. %s non importé.\n" % (i, champs_odoo[champ_fichier_sansrel]['description'], champ_fichier, ligne[champ_fichier], model_data['nom_objet'].capitalize()))
                            else:
                                erreur(u"Ligne %s : champ %s (%s) valeur \"%s\" n'a pas de correspondance. %s non importé.\n" % (i, champs_odoo[champ_fichier_sansrel]['description'], champ_fichier, ligne[champ_fichier], model_data['nom_objet'].capitalize()))

                # Si est un many2many
                elif champs_odoo[champ_fichier_sansrel]['type'] == 'many2many':
                    # C'est un many2many
                    # Ça équivaut à des étiquettes. On peut en importer plusieurs en les séparant par des virgules.
                    # Ex : étiquette1, étiquette2, étiquette3
                    tag_ids = []
                    if ligne[champ_fichier] and ligne[champ_fichier] != "#vide":  # S'il y a des données dans le champ d'import
                        ligne[champ_fichier] = ligne[champ_fichier].split(',')  # On sépare les étiquettes quand il y a une virgule
                        for tag in ligne[champ_fichier]:  # On parcourt les étiquettes à importer
                            # On regarde si elle existe.
                            res_ids = self.env[champs_odoo[champ_fichier_sansrel]['relation']].with_context(active_test=False).search([(champs_odoo[champ_fichier_sansrel]['relation_champ'] or 'name', '=', tag)])
                            if len(res_ids) == 1:
                                tag_ids.append(res_ids.id)
                            elif len(res_ids) > 1:
                                erreur(u"Ligne %s : champ %s (%s) valeur \"%s\" a plusieurs correspondances. %s non importé.\n" % (i, champs_odoo[champ_fichier_sansrel]['description'], champ_fichier, tag, model_data['nom_objet'].capitalize()))
                            else:
                                erreur(u"Ligne %s : champ %s (%s) valeur \"%s\" n'a pas de correspondance. %s non importé.\n" % (i, champs_odoo[champ_fichier_sansrel]['description'], champ_fichier, tag, model_data['nom_objet'].capitalize()))
                    if not erreur_msg[0]:
                        if ligne[champ_fichier] == "#vide":
                            valeurs[champ_fichier_sansrel] = [(5,)]
                        elif ligne[champ_fichier]:
                            valeurs[champ_fichier_sansrel] = [(6, 0, tag_ids)]

                # Pour tous les autres types de champ (char, text, date, ...)
                # On ne fait que prendre sa valeur sans traitement particulier
                else:
                    if ligne[champ_fichier] == "#vide":
                        valeurs[champ_fichier_sansrel] = ''
                    elif ligne[champ_fichier] != '':
                        valeur = ligne[champ_fichier]
                        if champ_fichier == model_data['champ_reference']:
                            if model == 'product.template':
                                # On ajoute à la référence d'un article le préfixe défini dans la marque associée
                                # Cette opération doit être réalisée après la détection de la marque mais avant la
                                #  détection du produit associé (la combinaison préfixe+référence est la clef de recherche)
                                brand_id = valeurs.get('brand_id')
                                if brand_id:
                                    brand = self.env['of.product.brand'].browse(brand_id)
                                else:
                                    brand = res_objet and res_objet.brand_id

                                if brand and brand.prefix:
                                    prefixe = brand.prefix + '_'
                                    # Le préfixe n'est ajouté que s'il n'est pas déjà appliqué (e.g. avec un export/import)
                                    if not valeur.startswith(prefixe):
                                        valeur = prefixe + valeur

                                # la référence de l'article est transférée dans les informations fournisseur
                                valeurs['of_seller_product_code'] = valeur
                            elif self.prefixe:
                                valeur = self.prefixe + valeur

                            if valeur:
                                libelle_ref = u"réf. " + valeur

                        valeurs[champ_fichier_sansrel] = valeur

            if champ_fichier and champ_fichier == model_data['champ_primaire']:
                # Récupération si possible de la valeur finale (par ex. si préfixe ajouté), sinon de la valeur dans le fichier (si champ non importable)
                valeur = valeurs.get(model_data['champ_primaire'], ligne[model_data['champ_primaire']])

                if valeur in doublons:
                    doublons[valeur][0] += 1
                    doublons[valeur][1] += ", " + str(i)
                    # Si la référence est un champ vide, on ne s'arrête pas, ça sera une création, mais on garde une copie des lignes pour faire un message d'avertissement.
                    if valeur != "":
                        erreur('')
                else:
                    doublons[valeur] = [1, str(i)]

                # On regarde si l'enregistrement existe déjà dans la base
                res_objet = model_obj.with_context(active_test=False).search([(model_data['champ_primaire'], '=', valeur)])

                if len(res_objet) > 1:
                    # Il existe plusieurs articles dans la base avec cette référence. On ne sait pas lequel mettre à jour. On passe au suivant en générant une erreur.
                    erreur(u"Ligne %s %s %s en plusieurs exemplaires dans la base, on ne sait pas lequel mettre à jour. %s non importé.\n" % (i, model_data['nom_objet'], libelle_ref, model_data['nom_objet'].capitalize()))
                    # Afin de continuer la simulation d'import correctement, on prend arbitrairement un des objets disponibles
                    # Evite notamment des erreurs pour la simulation d'import d'articles, car l'objet contient des paramètres d'import
                    res_objet = res_objet[0]

        try:
            self._post_calcule_ligne(champs_fichier, ligne, model_data, res_objet, valeurs)  # Champs à importer (pour envoi à fonction create ou write)
        except OfImportError, e:
            erreur(u"Ligne %s : %s %s non importé.\n" % (i, e.msg, model_data['nom_objet'].capitalize()))

        if not res_objet:
            # En cas de création, on doit vérifier que tous les champs Odoo requis ont bien été renseignés.
            for cle in champs_odoo:
                if champs_odoo[cle]['requis'] is True and cle not in valeurs:
                    erreur(u"Ligne %s : champ %s (%s) obligatoire mais non présent dans le fichier d'import. %s non importé.\n" % (i, champs_odoo[cle]['description'], cle, model_data['nom_objet'].capitalize()))

        message = erreur_msg[0]
        code = CODE_IMPORT_ERREUR
        if not message:
            if res_objet:
                # Il y a un (et un seul) enregistrement dans la base avec cette référence. On le met à jour.
                try:
                    if not simuler:
                        res_objet.write(valeurs)
                    code = CODE_IMPORT_MODIFICATION
                    message = u"MAJ %s %s (ligne %s)\n" % (model_data['nom_objet'], libelle_ref, i)
                except Exception, exp:
                    message = u"Ligne %s : échec mise à jour %s %s - Erreur : %s\n" % (i, model_data['nom_objet'], libelle_ref, exp)
            else:
                # L'enregistrement n'existe pas dans la base, on l'importe (création)
                try:
                    if not simuler:
                        model_obj.create(valeurs)
                    code = CODE_IMPORT_CREATION
                    message = u"Création %s %s (ligne %s)\n" % (model_data['nom_objet'], libelle_ref, i)
                except Exception, exp:
                    message = u"Ligne %s : échec création %s %s - Erreur : %s\n" % (i, model_data['nom_objet'], libelle_ref, exp)

        if not simuler:
            self._cr.commit()
        return code, message

    @api.multi
    def importer(self, simuler=True):

        # VARIABLES DE CONFIGURATION

        frequence_commit = 100  # Enregistrer (commit) tous les n enregistrements

        model = self.type_import  # On récupère l'objet (model) à importer indiqué dans le champ type d'import

        model_data = {
            'product.template': {
                'nom_objet': u'article',             # Libellé pour affichage dans message information/erreur
                'champ_primaire': 'default_code',    # Champ sur lequel on se base pour détecter si enregistrement déjà existant (alors mise à jour) ou inexistant (création)
                'champ_reference': 'default_code',   # Champ qui contient la référence ( ex : référence du produit, d'un client, ...) pour ajout du préfixe devant
            },
            'res.partner': {
                'nom_objet': u'partenaire',          # Libellé pour affichage dans message information/erreur
                'champ_primaire': 'ref',             # Champ sur lequel on se base pour détecter si enregistrement déjà existant (alors mise à jour) ou inexistant (création)
                'champ_reference': 'ref',            # Champ qui contient la référence ( ex : référence du produit, d'un client, ...) pour ajout du préfixe devant
                # 2 champs suivants : on récupère les id des types de compte comptable payable et recevable pour création comptes comptables clients et fournisseurs (généralement 411 et 401).
                'data_account_type_receivable_id': self.env['ir.model.data'].get_object_reference('account', 'data_account_type_receivable')[1],
                'data_account_type_payable_id': self.env['ir.model.data'].get_object_reference('account', 'data_account_type_payable')[1],
            },
            'of.service': {
                'nom_objet', u'service OpenFire',    # Libellé pour affichage dans message information/erreur
                'champ_primaire', 'id',              # Champ sur lequel on se base pour détecter si enregistrement déjà existant (alors mise à jour) ou inexistant (création)
                'champ_reference', '',               # Champ qui contient la référence ( ex : référence du produit, d'un client, ...) pour ajout du préfixe devant
            },
            'res.partner.bank': {
                'nom_objet': u'Comptes en banque partenaire',  # Libellé pour affichage dans message information/erreur
                'champ_primaire': 'acc_number',                # Champ sur lequel on se base pour détecter si enregistrement déjà existant (alors mise à jour) ou inexistant (création)
                'champ_reference': '',                         # Champ qui contient la référence ( ex : référence du produit, d'un client, ...) pour ajout du préfixe devant
            },
            'crm.lead': {
                'nom_objet': u'partenaire/opportunité',   # Libellé pour affichage dans message information/erreur
                'champ_primaire': 'of_ref',               # Champ sur lequel on se base pour détecter si enregistrement déjà existant (alors mise à jour) ou inexistant (création)
                'champ_reference': 'of_ref',              # Champ qui contient la référence ( ex : référence du produit, d'un client, ...) pour ajout du préfixe devant
            },
        }[model]
        model_data['model'] = model

        # Initialisation variables
        champs_odoo = self.get_champs_odoo(model)  # On récupère la liste des champs de l'objet (depuis ir.model.fields)
        date_debut = time.strftime('%Y-%m-%d %H:%M:%S')

        if simuler:
            sortie_succes = sortie_avertissement = sortie_erreur = u"SIMULATION - Rien n'a été créé/modifié.\n"
        else:
            sortie_succes = sortie_avertissement = sortie_erreur = u""

        nb_total = 0
        nb_ajout = 0
        nb_maj = 0
        nb_echoue = 0
        erreur = 0

        # LECTURE DU FICHIER D'IMPORT SELON EXTENSION (CHOISIR READER)
        # Le reader doit :
        # - Au premier appel, retourner la liste des noms des colonnes
        # - Aux appels suivants, retourner un dictionnaire clef:valeur de la prochaine ligne non vide ou lever une exception de type StopIteration
        # - S'assurer que chacune des valeurs retournées a subi un strip()
        reader = self._choisir_reader()

        # ANALYSE DES CHAMPS DU FICHIER D'IMPORT

        # On récupère la 1ère ligne du fichier (liste des champs) pour vérifier si des champs existent en plusieurs exemplaires
        champs_fichier = reader.next()

        if model == 'product.template':
            # Définition de l'ordre de lecture des champs. La marque doit être lue en premier
            champs_fichier = sorted(champs_fichier,
                                    key=lambda champ: (champ.split('/')[0] == 'brand_id' and 10) or
                                                      (champ == model_data['champ_reference'] and 20) or
                                                      (champ == model_data['champ_primaire'] and 30) or
                                                      40)

            # L'import de tarif nécessite l'existence de la marque associée aux articles
            if self.prefixe:
                default_brand = self.env['of.product.brand'].search([('prefix', '=', self.prefixe.rstrip('_'))])
                if default_brand:
                    model_data['default_brand_id'] = default_brand.id
                    if default_brand.partner_id:
                        model_data['default_seller_ids'] = [(5, ), (0, 0, {'name': default_brand.partner_id.id})]
                else:
                    erreur = 1
                    sortie_erreur += u"Aucune marque enregistrée ne correspond au préfixe %s.\n" % (self.prefixe, )
            else:
                for champ_fichier in champs_fichier:
                    champ_relation = champ_fichier.split('/')[0]
                    if champ_relation == 'brand_id':
                        break
                else:
                    sortie_erreur += u"Un préfixe doit être choisi pour l'import, ou une colonne du fichier doit définir la marque des articles\n"
        else:
            # Définition de l'ordre de lecture des champs. La marque doit être lue en premier
            champs_fichier = sorted(champs_fichier,
                                    key=lambda champ: (champ == model_data['champ_reference'] and 10) or
                                                      (champ == model_data['champ_primaire'] and 20) or
                                                      30)

        # Vérification si le champ primaire est bien dans le fichier d'import (si le champ primaire est défini)
        if model_data['champ_primaire'] and model_data['champ_primaire'] not in champs_fichier:
            erreur = 1
            sortie_erreur += u"Le champ référence qui permet d'identifier un %s (%s) n'est pas dans le fichier d'import.\n" % (model_data['nom_objet'], model_data['champ_primaire'])

        # Vérification si il y a des champs du fichier d'import qui sont en plusieurs exemplaires et détection champ relation (id, id externe, nom)
        doublons = {}

        for champ_fichier in champs_fichier:

            # Récupération du champ relation si est indiqué (dans le nom du champ après un /)
            champ_relation = champ_fichier[champ_fichier.rfind('/')+1 or len(champ_fichier):].strip()  # On le récupère.

            if champ_relation:  # Si est défini, on le retire du nom du champ.
                champ_fichier = champ_fichier[0:champ_fichier.rfind('/') if champ_fichier.rfind('/') != -1 else len(champ_fichier)].strip()

            if champ_fichier in doublons:
                doublons[champ_fichier] = doublons[champ_fichier] + 1
            else:
                doublons[champ_fichier] = 1

            # Test si est un champ de l'objet (sinon message d'information que le champ est ignoré à l'import)
            if champ_fichier not in champs_odoo:
                sortie_avertissement += u"Info : colonne \"%s\" dans le fichier d'import non reconnue. Ignorée lors de l'import.\n" % champ_fichier
            else:
                # Vérification que le champ relation (si est indiqué) est correct.
                if champ_relation and champs_odoo[champ_fichier]['type'] in ('many2one') and not champs_odoo[champ_fichier]['relation_champ']:
                    if not self.env['ir.model.fields'].search([('model', '=', champs_odoo[champ_fichier]['relation']),
                                                               ('name', '=', champ_relation)]):
                        sortie_erreur += u"Le champ relation \"%s\" (après le /) de la colonne \"%s\" n'existe pas.\n" % (champ_relation, champ_fichier)
                        erreur = 1
                    else:
                        champs_odoo[champ_fichier]['relation_champ'] = champ_relation
                elif champ_relation:
                    sortie_erreur += u"Un champ relation (après le /) dans la colonne \"%s\" n'est pas possible pour ce champ.\n" % champ_fichier
                    erreur = 1

        for champ_fichier in doublons:
            # On affiche un message d'avertissement si le champ existe en plusieurs exemplaires et si c'est un champ connu à importer
            if champ_fichier in champs_odoo and doublons[champ_fichier] > 1:
                sortie_erreur += u"La colonne \"%s\" dans le fichier d'import existe en %s exemplaires.\n" % (champ_fichier, doublons[champ_fichier])
                erreur = 1

        if erreur:  # On arrête si erreur
            self.write({'nb_total': nb_total, 'nb_ajout': nb_ajout, 'nb_maj': nb_maj, 'nb_echoue': nb_echoue, 'sortie_succes': sortie_succes, 'sortie_avertissement': sortie_avertissement, 'sortie_erreur': sortie_erreur})
            return

        # On ajoute le séparateur (caractère souligné) entre le préfixe et la référence si il n'a pas déjà été mis.
        prefixe = self.prefixe and self.prefixe.encode("utf-8") or ''
        if prefixe and prefixe[-1:] != '_':
            prefixe = prefixe + '_'

        doublons = {}  # Variable pour test si enregistrement en plusieurs exemplaires dans fichier d'import
        i = 1  # No de ligne

    #
    # IMPORT ENREGISTREMENT PAR ENREGISTREMENT
    #

        # On parcourt le fichier enregistrement par enregistrement
        while True:
            try:
                ligne = reader.next()
            except StopIteration:
                break

            if (nb_total + 1) % frequence_commit == 0:
                self.write({'nb_total': nb_total, 'nb_ajout': nb_ajout, 'nb_maj': nb_maj, 'nb_echoue': nb_echoue, 'sortie_succes': sortie_succes, 'sortie_avertissement': sortie_avertissement, 'sortie_erreur': sortie_erreur})

            i = i + 1
            nb_total += 1

            try:
                code, message = self._importer_ligne(ligne, champs_fichier, champs_odoo, i, model_data, doublons, simuler)

                if message:
                    if code == CODE_IMPORT_ERREUR:
                        sortie_erreur += message
                    else:
                        sortie_succes += message
            except OfImportError, e:
                code = CODE_IMPORT_ERREUR
                sortie_erreur += e.msg

            if code == CODE_IMPORT_ERREUR:
                nb_echoue += 1
            elif code == CODE_IMPORT_CREATION:
                nb_ajout += 1
            elif code == CODE_IMPORT_MODIFICATION:
                nb_maj += 1

        # On affiche les enregistrements qui étaient en plusieurs exemplaires dans le fichier d'import.
        for cle in doublons:
            if cle == "":
                sortie_avertissement += u"ATTENTION : les enregistrements suivants ont été créés mais ont un champ référence vide (risque de doublon en cas d'import en plusieurs passes) : ligne(s) %s.\n" % (doublons[cle][1])
            elif doublons[cle][0] > 1:
                sortie_avertissement += u"%s réf. %s existe en %s exemplaires dans le fichier d'import (lignes %s). Seule la première ligne est importée.\n" % (model_data['nom_objet'].capitalize(), cle, doublons[cle][0], doublons[cle][1])

        # On enregistre les dernières lignes qui ne l'auraient pas été.
        self.write({'nb_total': nb_total, 'nb_ajout': nb_ajout, 'nb_maj': nb_maj, 'nb_echoue': nb_echoue, 'sortie_succes': sortie_succes, 'sortie_avertissement': sortie_avertissement, 'sortie_erreur': sortie_erreur, 'date_debut_import' : date_debut, 'date_fin_import' : time.strftime('%Y-%m-%d %H:%M:%S')})

        if not simuler:
            self.write({'state': 'importe'})

        return
