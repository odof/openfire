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
from odoo.exceptions import except_orm, UserError, ValidationError

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

# class OfImportError(Exception):
#     def __init__(self, msg):
#         self.msg = msg
class OfImportError(except_orm):
    def __init__(self, msg):
        super(OfImportError, self).__init__(msg)

class OfImportProductConfigTemplate(models.AbstractModel):
    _name = 'of.import.product.config.template'
    _description = u"Classe regroupant les paramètres personnalisables dans la configuration d'import de tarifs"

    of_import_price = fields.Char(string='Prix de vente HT',
                                  help=u"""Modification à appliquer sur le prix public hors taxe pour calculer le prix de vente.

Exemples :
 ppht : Conserve le prix de vente conseillé (prix public hors taxe)
 ppht * 1.05 + 10 : Augmente le prix de vente de 5%, plus 10€
 pa * 100 / 60 : Vend l'article pour obtenir une marge de 40% sur le prix d'achat (et non sur le prix de revient!)""")
    of_import_remise = fields.Char(string="Remise",
                                   help=u"""Remise à appliquer sur les articles de ce fournisseur.
La remise est appliquée sur le prix public pour calculer le prix d'achat.

Exemples :
 40.5 : Forcer une remise de 40,5% (Attention, utiliser un . et non pas une virgule!)
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

    @api.constrains('of_import_price', 'of_import_remise', 'of_import_cout')
    def _check_description(self):
        """
        Fonction de vérification de la validité des formules saisies.
        Une formule, si renseignée, ne peut pas être constituée uniquement d'espaces blancs.
        Une formule doit être évaluable sans erreur, avec les variables fournies dans eval_dict.
        Une formule, si renseignée, doit retourner une valeur de type numérique (entier ou flottant).
        """
        # Jeu de valeurs pour tester la validité des formules saisies
        eval_dict = {
            'ppht' : 100,
            'cumul': self.env['of.product.brand'].compute_remise,
            'pa'   : 50,
        }

        for record in self:
            for field in (
                'of_import_price',
                'of_import_remise',
                'of_import_cout',
            ):
                code = record[field]
                if not code:
                    continue
                if not code.strip():
                    raise ValidationError(u"Une formule ne doit pas être constituée uniquement d'espaces.\n\n"
                                          u"Vous devez vider le champ, ou le renseigner avec une formule correcte s'il est obligatoire : (champ \"%s\", formule \"%s\")" % (self._fields[field].string, code))
                try:
                    value = safe_eval(code, eval_dict)
                except Exception, e:
                    raise ValidationError(u"Une erreur s'est produite à la validation de la formule : (champ \"%s\", formule \"%s\")\n\n"
                                          u"Erreur :\n%s" % (self._fields[field].string, code, e))
                if value and not isinstance(value, (int, long, float)):
                    raise ValidationError(u"Le format de retour de la fonction n'est pas celui attendu : (champ \"%s\", formule \"%s\")\n\n"
                                          u"Cette erreur peut se produire si vous avez utilisé une virgule au lieu d'un point comme séparateur de décimales." % (self._fields[field].string, code))

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
    product_ids = fields.One2many('product.template', string="Articles", compute="_compute_product_ids")

    @api.depends('categ_origin', 'brand_id.product_ids', 'brand_id.product_ids.of_seller_product_category_name')
    def _compute_product_ids(self):
        product_obj = self.env['product.template']
        for categ in self:
            categ.product_ids = product_obj.search([('brand_id', '=', categ.brand_id.id), ('seller_ids.of_product_category_name', '=', categ.categ_origin)])

    _sql_constraints = [
        ('categ_origin_uniq', 'unique(brand_id, categ_origin)', u"Une catégorie de produits ne peut être renseignée qu'une fois"),
    ]

    @api.multi
    def action_update_products(self):
        """
        Recalcule les champs des articles en fonction de la configuration de la marque
        et des paramètres d'import de l'article (dans product_supplierinfo)
        """
        self.mapped('product_ids').of_action_update_from_brand()

class OFProductBrand(models.Model):
    _name = 'of.product.brand'
    _inherit = ('of.product.brand', 'of.import.product.config.template')

    categ_ids = fields.One2many('of.import.product.categ.config', 'brand_id', string="Catégories")
    product_config_ids = fields.One2many('product.template', string="Articles", compute="_compute_product_config_ids",
                                         inverse="_inverse_product_config_ids", domain="[('brand_id', '=', id)]")

    of_import_price = fields.Char(required=True, default='ppht')
    of_import_cout = fields.Char(required=True, default="pa")
    of_import_categ_id = fields.Many2one(required=True)

    @api.depends('product_ids.of_import_price', 'product_ids.of_import_remise', 'product_ids.of_import_categ_id')  # , 'product_ids.of_import_price_extra'
    def _compute_product_config_ids(self):
        product_obj = self.env['product.template']
        fields = self.get_config_field_list()
        domain = ['|'] * (len(fields) - 1) + [(field, '!=', False) for field in fields]
        for brand in self:
            brand.product_config_ids = product_obj.search([('brand_id', '=', brand.id)] + domain)

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

        # Enfin, dernière solution, retour de la catégorie par défaut pour la marque
        return self.of_import_categ_id

    @api.multi
    def compute_product_price(self, list_price, categ_name, uom, uom_po, product=None, price=None, remise=None):
        """
        @param categ_name: Nom de la catégorie de produit telle que donnée par le fournisseur
        @param product: Objet product.template si existant sur la base actuellement
        @param price: Prix d'achat pouvant être utilisé si aucune formule n'est renseignée pour la remise
        """
        self.ensure_one()

        categ_config = self.env['of.import.product.categ.config'].search([('brand_id', '=', self.id), ('categ_origin', '=', categ_name)])

        udm_ratio = uom_po._compute_price(1.0, uom) if uom_po else 1.0
        eval_dict = {
            'ppht' : list_price,
            'cumul': self.compute_remise,
            'udm_ratio': udm_ratio,
        }

        fields = (('of_import_remise', 'remise', 'la remise'),
                  ('of_import_price', 'list_price', 'le prix de vente HT'),
                  ('of_import_cout', 'standard_price', u'le coût'))
        values = {}
        for config_field, product_field, text in fields:
            for obj in (product, categ_config, self):
                if obj and obj[config_field]:
                    value = safe_eval(obj[config_field], eval_dict)
                    if product_field == 'remise':
                        # Une fois la remise calculée, on peut ajouter le prix d'achat au eval_dict pour le calcul du coût final
                        eval_dict['pa'] = list_price * (100.0 - value) / 100.0
                    else:
                        values[product_field] = value
                    break
            else:
                # Aucune formule n'a été renseignée. Cette formule n'est pas obligatoire pour la remise
                if product_field == 'remise':
                    # Si la formule de la remise n'est pas renseignée, le prix d'achat d'origine est conservé
                    if price is not None:
                        # Le prix est renseigné au niveau de l'import
                        eval_dict['pa'] = price
                    elif remise is not None:
                        # La remise est renseignée au niveau de l'import
                        eval_dict['pa'] = list_price * (100.0 - remise) / 100.0
                    elif product:
                        # L'article existe déjà, son prix d'achat est conservé
                        eval_dict['pa'] = product.of_seller_price
                    else:
                        # La formule n'est pas renseignée et aucune valeur ne peut être déduite
                        raise OfImportError(u"Aucune formule n'est renseignée pour %s de cet article (marque à configurer : %s)." % (text, self.name))
                else:
                    raise OfImportError(u"Aucune formule n'est renseignée pour %s de cet article (marque à configurer : %s)." % (text, self.name))

        values['of_seller_price'] = eval_dict['pa']
        values['list_price'] *= udm_ratio
        values['standard_price'] *= udm_ratio

        return values

    @api.multi
    def compute_product_values(self, list_price, categ_name, uom_id, uom_po_id, product=None, price=None, remise=None):
        self.ensure_one()

        categ = self.compute_product_categ(categ_name, product=product)
        if not categ:
            raise UserError(u"Impossible de trouver la catégorie de produits correspondant à \"%s\"" % (categ_name, ))

        values = self.compute_product_price(list_price, categ_name, uom_id, uom_po_id, product=product, price=price, remise=remise)
        values['categ_id'] = categ.id
        return values

    @api.multi
    def action_update_products(self):
        """
        Recalcule les champs de l'article en fonction de la configuration de la marque
        et des paramètres d'import de l'article (dans product_supplierinfo)
        """
        self.mapped('product_ids').of_action_update_from_brand()

class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = ('product.template', 'of.import.product.config.template')

    @api.multi
    def of_action_update_from_brand(self):
        """
        Recalcule les champs de l'article en fonction de la configuration de la marque
        et des paramètres d'import de l'article (dans product_supplierinfo)
        """
        # On prétend venir d'un import afin de lancer la propagation du coût sur les différentes sociétés
        self = self.with_context(from_import=True)
        for product in self:
            supplier = product.brand_id.partner_id
            for seller in product.seller_ids:
                if seller.name == supplier:
                    values = product.brand_id.compute_product_values(
                        seller.pp_ht,
                        seller.of_product_category_name,
                        product.uom_id,
                        product.uom_po_id,
                        product
                    )
                    values = {key: val for key, val in values.iteritems() if self._fields[key].convert_to_write(product[key], product) != val}
                    if values:
                        product.write(values)
                    break

class OfImport(models.Model):
    _name = 'of.import'
    _order = 'date desc'

    @api.model
    def _default_lang_id(self):
        lang = self.env['res.lang'].search([('code', '=', 'en_US')])
        if not lang:
            lang = self.env['res.lang'].search([('code', '=', self.env.lang)])
        return lang

    user_id = fields.Many2one('res.users', u'Utilisateur', readonly=True, default=lambda self: self._uid)

    name = fields.Char(u'Nom', size=64, required=True)
    type_import = fields.Selection([('product.template', u'Articles'), ('res.partner', u'Partenaires'), ('crm.lead', u'Pistes/opportunités'), ('res.partner.bank', u'Comptes en banques partenaire'), ('of.service', u'Services OpenFire')], string=u"Type d'import", required=True)
    lang_id = fields.Many2one('res.lang', string="Langue principale", default=lambda self: self._default_lang_id())
    show_lang = fields.Boolean(compute='_compute_show_lang', string="Afficher la langue principale")

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

    @api.multi
    @api.depends('lang_id')
    def _compute_show_lang(self):
        if self.env['res.lang'].search([('code', '=', 'en_US')]):
            # Si la langue américaine est installée, elle est obligatoirement la langue principale
            show_lang = False
        else:
            # Si une seule langue est installée, elle est obligatoirement la langue principale
            show_lang = self.env['res.lang'].search([('translatable', '=', True)], count=True) > 1
        for imp in self:
            imp.show_lang = show_lang

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

    @api.depends('type_import', 'lang_id')
    def _compute_sortie_note(self):
        "Met à jour la liste des champs Odoo disponibles pour l'import dans le champ note"
        for imp in self:
            sortie_note = ''
            for champ, valeur in sorted(self.get_champs_odoo(imp.type_import, imp.lang_id.code or self.env.lang).items(),
                                        key=lambda v: (v[1]['description'], v[0])):
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

    # --- READERS ---
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

    # OPENOFFICE
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

    # MS OFFICE
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

    @api.model
    def get_champs_odoo(self, model='', lang=False):
        "Renvoie un dictionnaire contenant les caractéristiques des champs Odoo en fonction du type d'import sélectionné (champ type_import)"

        if not model:
            return {}

        champs_odoo = {}

        langues = self.env['res.lang'].search([('translatable', '=', True), ('active', '=', True)]).mapped('code')
        if len(langues) == 1:
            # Si il n'y a qu'une langue active, Odoo ne s'occupe pas des traductions.
            langues = []
        else:
            langues = [langue for langue in langues if langue != 'en_US' and langue != lang]

        # On récupère la liste des champs de l'objet depuis ir.model.fields
        obj = self.env['ir.model.fields'].search([('model', '=', model)])
        for champ in obj:
            field = self.env[model]._fields[champ.name]
            if (field.compute or not field.store) and not field.inverse:
                continue
            champs_odoo[champ.name] = {
                'description': champ.field_description,
                'requis': champ.required,
                'type': champ.ttype,
                'relation': champ.relation,
                'relation_champ': champ.relation_field,
                'langue': False,
                'traduit': champ.translate,
            }

            if champ.translate:
                for langue in langues:
                    champs_odoo["[%s]%s" % (langue, champ.name)] = {
                        'description': champ.field_description,
                        'requis': False,
                        'type': champ.ttype,
                        'relation': champ.relation,
                        'relation_champ': champ.relation_field,
                        'langue': langue,
                        'traduit': False,
                    }

        # Des champs qui sont obligatoires peuvent avoir une valeur par défaut (donc in fine pas d'obligation de les renseigner).
        # On récupère les champs qui ont une valeur par défaut et on indique qu'ils ne sont pas obligatoires.
        champs_requis = [key for key, vals in champs_odoo.iteritems() if vals['requis']]
        for key, val in self.env[model].default_get(champs_requis).iteritems():
            champs_odoo[key]['requis'] = val is False

        # On ne rend pas obligatoire manuellement un champ qui est marqué comme obligatoire car créé par la fonction create d'Odoo.
        if model == 'product.template':
            if 'product_variant_ids' in champs_odoo:
                champs_odoo['product_variant_ids']['requis'] = False

            if 'brand_id' in champs_odoo:
                # Dans le cadre de l'import de tarif, on rend obligatoire le renseignement de la marque de l'article
                champs_odoo['brand_id']['requis'] = True

            if 'categ_id' in champs_odoo:
                # Le champ categ_id importé est la catégorie du fournisseur. Le vrai categ_id sera calculé en fonction de la marque
                champs_odoo['categ_id']['requis'] = False

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

    # --- IMPORT ---
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
            uom_obj = self.env['product.uom']
            brand_id = valeurs.get('brand_id')
            if brand_id:
                brand = self.env['of.product.brand'].browse(brand_id)
            else:
                brand = res_objet.brand_id
                # Si brand n'est pas défini, une exception sera automatiquement générée plus tard
                # car la marque est un champ obligatoire pour l'import de tarif

            if 'categ_id' in champs_fichier and 'categ_id' not in valeurs:
                # Si la catégorie d'article n'est pas renseignée, on prend la catégorie par défaut de la marque
                valeurs['categ_id'] = brand.compute_product_categ(res_objet and res_objet.of_seller_product_category_name or '', product=res_objet).id

            # Calcul des prix d'achat/vente en fonction des règles de calcul et du prix public ht
            if 'list_price' in valeurs and brand:
                valeurs['of_seller_pp_ht'] = valeurs['list_price']
                valeurs.update(brand.compute_product_price(valeurs['list_price'],
                                                           valeurs.get('of_seller_product_category_name', res_objet and res_objet.of_seller_product_category_name or ''),
                                                           uom_obj.browse(valeurs['uom_id']),
                                                           uom_obj.browse(valeurs['uom_po_id']),
                                                           product=res_objet,
                                                           price=valeurs.get('of_seller_price'),
                                                           remise=valeurs.get('of_seller_remise')))

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
        # Pour gérer les traductions, on importe d'abord avec la langue par défaut (en_US),
        # puis on met à jour les champs pour chaque valeur traduite importée
        self = self.with_context(lang='en_US')
        valeurs_trad = {}

        model = self.type_import
        model_obj = self.env[model_data['model']].with_context(from_import=True)
        product_categ_obj = self.env['product.category']
        product_categ_config_obj = self.env['of.import.product.categ.config']

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
                    if model == 'product.template' and champ_fichier == 'categ_id':
                        valeurs['of_seller_product_category_name'] = ligne[champ_fichier]
                        if ligne[champ_fichier] == '#vide':
                            # Avoir une catégorie non renseignée côté fournisseur n'empêche pas de calculer celle du distributeur grâce à la marque
                            ligne[champ_fichier] = '.'
                            valeurs['of_seller_product_category_name'] = ''
                        elif ligne[champ_fichier] == '':
                            # A chaque import les informations fournisseur sont supprimées et regénérées. Il faut dans ce cas les récupérer
                            if res_objet:
                                ligne[champ_fichier] = '.'
                                valeurs['of_seller_product_category_name'] = res_objet.of_seller_product_category_name or ''
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
                            ligne[champ_fichier] = valeurs['of_seller_product_category_name']

                            brand = valeurs.get('brand_id') and self.env['of.product.brand'].browse(valeurs['brand_id'])
                            if res_objet and not brand:
                                brand = res_objet.brand_id

                            if brand and simuler:
                                # Lors d'une simulation, les catégories manquantes sont ajoutées à la configuration de la marque
                                if not product_categ_config_obj.search([('brand_id', '=', brand.id), ('categ_origin', '=', ligne[champ_fichier])]):
                                    categ = product_categ_obj.search([('name', '=', ligne[champ_fichier])])
                                    product_categ_config_obj.create({
                                        'brand_id': brand.id,
                                        'categ_origin': ligne[champ_fichier],
                                        'of_import_categ_id': categ and len(categ) == 1 and categ.id or False,
                                    })

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
                    # La gestion des traductions de champs se fera à part

                    if champs_odoo[champ_fichier_sansrel]['traduit'] and ligne[champ_fichier] != '':
                        lang = self.lang_id.code or 'en_US'
                        if lang != 'en_US':
                            vals_trad = valeurs_trad.setdefault(lang, {})
                            vals_trad[champ_fichier_sansrel] = '' if ligne[champ_fichier] == "#vide" else ligne[champ_fichier]
                    if champs_odoo[champ_fichier_sansrel]['langue']:
                        if ligne[champ_fichier] != '':
                            lang = champs_odoo[champ_fichier_sansrel]['langue']
                            vals_trad = valeurs_trad.setdefault(lang, {})
                            vals_trad[champ_fichier_sansrel[len(lang) + 2:]] = '' if ligne[champ_fichier] == "#vide" else ligne[champ_fichier]
                    elif ligne[champ_fichier] == "#vide":
                        valeurs[champ_fichier_sansrel] = ''
                    elif ligne[champ_fichier] != '':
                        valeur = ligne[champ_fichier]
                        if champ_fichier == model_data['champ_reference']:
                            if model == 'product.template':
                                # On ajoute (ou retire) à la référence d'un article le préfixe défini dans la marque associée
                                # Cette opération doit être réalisée après la détection de la marque mais avant la
                                #  détection du produit associé (la combinaison préfixe+référence est la clef de recherche)
                                brand_id = valeurs.get('brand_id')
                                if brand_id:
                                    brand = self.env['of.product.brand'].browse(brand_id)
                                else:
                                    brand = res_objet.brand_id

                                if brand:
                                    prefixe = brand.code + '_'
                                    if brand.use_prefix:
                                        # Le préfixe n'est ajouté que s'il n'est pas déjà appliqué (e.g. avec un export/import)
                                        if not valeur.startswith(prefixe):
                                            valeur = prefixe + valeur
                                    else:
                                        if valeur.startswith(prefixe):
                                            valeur = valeur[len(prefixe):]

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
                domain = [(model_data['champ_primaire'], '=', valeur)]
                if model == 'product.template':
                    # Pour un article, la clef est le champ primaire ET la marque.
                    # Un article sans marque (créé avant l'installation du module of_product_brand) est également valide.
                    if valeurs.get('brand_id'):
                        domain += ['|', ('brand_id', '=', False), ('brand_id', '=', valeurs['brand_id'])]
                    else:
                        domain += [('brand_id', '=', False)]
                res_objet = model_obj.with_context(active_test=False).search(domain)

                if model == 'product.template' and len(res_objet) > 1:
                    # Plusieurs articles trouvés, recherche sur la marque
                    res_objet = res_objet.filtered(lambda o: o.brand_id == valeurs.get('brand_id')) or res_objet

                if len(res_objet) > 1:
                    # Il existe plusieurs articles dans la base avec cette référence. On ne sait pas lequel mettre à jour. On passe au suivant en générant une erreur.
                    erreur(u"Ligne %s %s %s en plusieurs exemplaires dans la base, on ne sait pas lequel mettre à jour. %s non importé.\n" % (i, model_data['nom_objet'], libelle_ref, model_data['nom_objet'].capitalize()))
                    # Afin de continuer la simulation d'import correctement, on prend arbitrairement un des objets disponibles
                    # Evite notamment des erreurs pour la simulation d'import d'articles, car l'objet contient des paramètres d'import
                    res_objet = res_objet[0]

        try:
            self._post_calcule_ligne(champs_fichier, ligne, model_data, res_objet, valeurs)  # Champs à importer (pour envoi à fonction create ou write)
        except OfImportError, e:
            erreur(u"Ligne %s : %s %s non importé.\n" % (i, e.name, model_data['nom_objet'].capitalize()))

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
                        for lang, vals in valeurs_trad.iteritems():
                            res_objet.with_context(lang=lang).write(vals)
                    code = CODE_IMPORT_MODIFICATION
                    message = u"MAJ %s %s (ligne %s)\n" % (model_data['nom_objet'], libelle_ref, i)
                except Exception, exp:
                    message = u"Ligne %s : échec mise à jour %s %s - Erreur : %s\n" % (i, model_data['nom_objet'], libelle_ref, str(exp).decode('utf8', 'ignore'))
            else:
                # L'enregistrement n'existe pas dans la base, on l'importe (création)
                try:
                    if not simuler:
                        res_objet = model_obj.create(valeurs)
                        for lang, vals in valeurs_trad.iteritems():
                            res_objet.with_context(lang=lang).write(vals)
                    code = CODE_IMPORT_CREATION
                    message = u"Création %s %s (ligne %s)\n" % (model_data['nom_objet'], libelle_ref, i)
                except Exception, exp:
                    message = u"Ligne %s : échec création %s %s - Erreur : %s\n" % (i, model_data['nom_objet'], libelle_ref, str(exp).decode('utf8', 'ignore'))

        if not simuler:
            if code == CODE_IMPORT_ERREUR:
                # Si l'erreur est de type SQL, le cursor est en 'ABORT STATE' et commit() et rollback()
                #   ont le même effet.
                # En revanche, si l'erreur est une erreur python, le cursor est correct et un commit()
                #   risque de valider un import incomplet.
                self._cr.rollback()
            else:
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
                'nom_objet': u'service OpenFire',    # Libellé pour affichage dans message information/erreur
                'champ_primaire': 'id',              # Champ sur lequel on se base pour détecter si enregistrement déjà existant (alors mise à jour) ou inexistant (création)
                'champ_reference': '',               # Champ qui contient la référence ( ex : référence du produit, d'un client, ...) pour ajout du préfixe devant
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
        champs_odoo = self.get_champs_odoo(model, self.lang_id.code or self.env.lang)  # On récupère la liste des champs de l'objet (depuis ir.model.fields)
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
                default_brand = self.env['of.product.brand'].search([('code', '=', self.prefixe.rstrip('_'))])
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

            # Les udm des articles seront nécessaires pour le calcul des prix de revient et de vente
            for key, val in self.env['product.template'].default_get(('uom_id', 'uom_po_id')).iteritems():
                model_data['default_' + key] = val

            # L'import de tarif est susceptible d'ajouter des lignes de configuration dans les marques.
            # On sauvegarde l'état actuel pour récupérer les lignes nouvellement créées
            product_categ_config_obj = self.env['of.import.product.categ.config']
            product_categ_config_ids = product_categ_config_obj.search([]).ids
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
                if champ_relation and champs_odoo[champ_fichier]['type'] in ('many2one', ) and not champs_odoo[champ_fichier]['relation_champ']:
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
                sortie_avert = sortie_avertissement
                if model == 'product.template':
                    product_categ_configs = product_categ_config_obj.search([('id', 'not in', product_categ_config_ids)], order='brand_id, categ_origin')
                    if product_categ_configs:
                        sortie_avert = "\n".join([u"Marque %s : Ajout de la configuration pour la catégorie \"%s\"" % (config.brand_id.name, config.categ_origin) for config in product_categ_configs]) + "\n\n" + sortie_avert
                self.write({'nb_total': nb_total, 'nb_ajout': nb_ajout, 'nb_maj': nb_maj, 'nb_echoue': nb_echoue, 'sortie_succes': sortie_succes, 'sortie_avertissement': sortie_avert, 'sortie_erreur': sortie_erreur})

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
                sortie_erreur += e.name

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
        sortie_avert = sortie_avertissement
        if model == 'product.template':
            product_categ_configs = product_categ_config_obj.search([('id', 'not in', product_categ_config_ids)], order='brand_id, categ_origin')
            if product_categ_configs:
                sortie_avert = "\n".join([u"Marque %s : Ajout de la configuration pour la catégorie \"%s\" (%s correspondance)" % (config.brand_id.name, config.categ_origin, config.of_import_categ_id and 'avec' or 'sans') for config in product_categ_configs]) + "\n\n" + sortie_avert
        self.write({'nb_total': nb_total, 'nb_ajout': nb_ajout, 'nb_maj': nb_maj, 'nb_echoue': nb_echoue, 'sortie_succes': sortie_succes, 'sortie_avertissement': sortie_avert, 'sortie_erreur': sortie_erreur, 'date_debut_import' : date_debut, 'date_fin_import' : time.strftime('%Y-%m-%d %H:%M:%S')})

        if not simuler:
            self.write({'state': 'importe'})

        return
