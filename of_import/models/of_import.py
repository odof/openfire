# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import time
from os import path

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import config

from .of_import_error import OfImportError
from .utils import _get_odoo_fields_attachment, _read_csv, _read_xls, _read_xlsx

try:
    import chardet
except ImportError:
    chardet = None


EXTENSIONS = ('csv', 'xls', 'xlsx')
SELECT_EXTENSIONS = [
    ('csv', 'CSV'),
    ('xls', 'MS-Excel'),
    ('xlsx', 'MS-Excel-10'),
]

IMPORT_ERROR_CODE = -1
IMPORT_WARNING_CODE = -2
IMPORT_CREATION_CODE = 0
IMPORT_MODIFICATION_CODE = 1


class OfImport(models.Model):
    _name = 'of.import'
    _order = 'date desc'

    @api.model
    def _default_lang_id(self):
        res_lang_obj = self.env['res.lang']
        return res_lang_obj.search([('code', '=', 'en_US')]) or res_lang_obj.search([('code', '=', self.env.lang)])

    name = fields.Char(size=64, required=True)
    user_id = fields.Many2one(
        comodel_name='res.users', string="User", readonly=True, default=lambda self: self.env.user
    )
    lang_id = fields.Many2one(
        comodel_name='res.lang', string="Main Language", default=lambda self: self._default_lang_id()
    )
    type_import = fields.Selection(selection='_selection_type_import', string="Type of import", required=True)
    show_lang = fields.Boolean(compute='_compute_show_lang', string="Show Main Language")
    prefix = fields.Char(string="Reference prefix", size=10, help="Text that will precede the reference.")
    output_note = fields.Text(string="Note", compute='_compute_output_note')
    state = fields.Selection(
        selection=[
            ('draft', "Draft"),
            ('imported', "Imported"),
            ('canceled', "Canceled"),
        ],
        default='draft',
        readonly=True,
    )

    # Dates and times
    date = fields.Datetime(
        required=True,
        default=fields.Datetime.now,
        help="Date to be assigned to imports as the value date.",
    )
    date_start_import = fields.Datetime(string="Start", readonly=True)
    date_end_import = fields.Datetime(string="End", readonly=True)
    time_lapse = fields.Char(string="Import in", compute='_compute_time_lapse')

    # File
    file = fields.Binary(required=True)
    file_name = fields.Char(string="Filename")
    file_type = fields.Selection(selection=SELECT_EXTENSIONS, compute='_compute_file_type')
    file_size = fields.Char(string="File size", compute='_compute_file_size')
    separator = fields.Char(
        string="Field separator",
        help="""Field separator character in the import file.
    If not specified, the system will attempt to determine it automatically.
    Use \\t for tabulation.""",
    )

    # Counters
    total_count = fields.Integer(readonly=True)
    added_count = fields.Integer(readonly=True)
    updated_count = fields.Integer(readonly=True)
    failed_count = fields.Integer(readonly=True)
    ignored_count = fields.Integer(readonly=True)

    # Messages
    import_success_ids = fields.One2many(
        comodel_name='of.import.message',
        inverse_name='import_id',
        string="Success",
        readonly=True,
        domain=[('type', '=', 'info')],
    )
    import_warning_ids = fields.One2many(
        comodel_name='of.import.message',
        inverse_name='import_id',
        string="Warnings",
        readonly=True,
        domain=[('type', '=', 'warning')],
    )
    import_error_ids = fields.One2many(
        comodel_name='of.import.message',
        inverse_name='import_id',
        string="Errors",
        readonly=True,
        domain=[('type', '=', 'error')],
    )

    # ---------------------------------------------------------------------
    # Compute methods
    # ---------------------------------------------------------------------

    @api.model
    def _selection_type_import(self):
        """
        Fonction de calcul de la sélection disponible pour le type d'import.
        En effet, certains objets (product.pack.line, of.service.request) proviennent de modules qui ne sont pas dans
        les dépendances du module of_import.
        """
        # TODO: Improve this method to avoid hardcoding the model names
        selection = [
            ('product.template', _("Products")),
            ('product.pack.line', _("Kit components")),
            ('res.partner.bank', _("Partner bank journals")),
            ('ir.attachment', _("Images/Attachments")),
            ('res.partner', _("Partners")),
            ('crm.lead', _("CRM/Leads")),
            ('of.service.request', _("Services requests")),
        ]
        return [s for s in selection if s[0] in self.env]

    @api.depends('lang_id')
    def _compute_show_lang(self):
        if self.env['res.lang'].search([('code', '=', 'en_US')]):
            # Si la langue américaine est installée, elle est obligatoirement la langue principale
            show_lang = False
        else:
            # Si une seule langue est installée, elle est obligatoirement la langue principale
            show_lang = self.env['res.lang'].search([('active', '=', True)], count=True) > 1
        for record in self:
            record.show_lang = show_lang

    @api.depends('file', 'file_name')
    def _compute_file_type(self):
        """Get file type par extension ('csv', 'xls', 'xlsx')"""
        for record in self:
            if file_name := record.file_name:
                splitted = file_name.split(".")
                if len(splitted) <= 1:
                    raise UserError(_("Unrecognized file type !"))
                extension = splitted[-1]
                if extension not in EXTENSIONS:
                    raise UserError(_("Unrecognized file type !"))
                record.file_type = extension
            else:
                record.file_type = False

    @api.depends('file')
    def _compute_file_size(self):
        for record in self:
            if record.file and len(record.file) > 20 or not record.file:
                record.file_size = "--"
            else:
                record.file_size = record.file

    @api.depends('date_start_import', 'date_end_import')
    def _compute_time_lapse(self):
        for record in self:
            if record.date_start_import and record.date_end_import:
                record.time_lapse = record.date_end_import - record.date_start_import
            else:
                record.time_lapse = False

    @api.depends('type_import', 'lang_id')
    def _compute_output_note(self):
        """Met à jour la liste des champs Odoo disponibles pour l'import dans le champ note"""
        for record in self:
            output_note = ""
            for field, value in sorted(
                self._get_odoo_fields(record.type_import, record.lang_id.code or self.env.lang).items(),
                key=lambda v: (v[1]['description'], v[0]),
            ):
                if field in ('tz', 'lang'):  # don't want to manage these fields
                    continue
                output_note += f"- {value['description'] or ''} : {field}"
                if value['type'] == 'selection':
                    key_list = " ".join(self.env[self.type_import]._fields[field].get_values(self.env))
                    output_note += _(" [ authorized values : %(key_list)s ]", key_list=key_list)
                output_note += '\n'

            if output_note:
                output_note = _(
                    "Fields available for import (column headers) :\n %(output_note)s", output_note=output_note
                )
            record.output_note = output_note

    # ---------------------------------------------------------------------
    # Action methods
    # ---------------------------------------------------------------------

    def action_button_set_draft(self):
        self.write({'state': 'draft'})
        self.mapped('import_success_ids').unlink()
        self.mapped('import_warning_ids').unlink()
        self.mapped('import_error_ids').unlink()
        return True

    def action_button_simulate(self):
        return self.action_import(simulate=True)

    def action_button_import(self):
        return self.action_import(simulate=False)

    def action_import_line(self, line, file_fields, fields_odoo, i, model_data, duplicates, simulate):
        """
        Cas de l'import d'articles :
        --------------------------------
        Lors de l'import d'articles, la marque est un élément obligatoire qui peut être déduit du préfixe d'import ou
            calculé ligne par ligne dans une colonne dédiée du fichier importé.
        Le calcul de la marque doit être réalisé avant toute chose.
        En effet, il conditionne le préfixe ajouté à la référence de l'article, laquelle permet d'identifier un article
            déjà existant en DB, lequel pouvant définir des paramètres d'import pour forcer la catégorie de produit.

        L'ordre logique du processus d'import est donc :
            1 - Détection de la marque
            2 - Mise à jour de la référence de l'article avec le préfixe de la marque
                (si non déjà inclus, par exemple avec export+import)
            3 - Détection d'article existant, impliquant une mise à jour et non une création de nouvel article
            4 - Import des éléments du fichier

        L'import de la catégorie de produit ne se fait pas dans _post_compute_line() car il s'agit d'un champ one2many,
            on s'évite de recopier le processus de lecture de ce champ ainsi que la fonction erreur()
            ce qui facilitera les mises à jour futures
        """
        import_errors = []
        code = 0

        def add_error(msg):
            if msg:
                import_errors.append(Command.create({'type': 'error', 'message': msg}))
            if not simulate:  # not simulate, we raise the error
                raise OfImportError(import_errors)

        # On se place dans la langue du fichier d'import (notamment pour la recherche des champs many2one).
        if self.lang_id.code and self.lang_id.code != self.env.lang:
            self = self.with_context(lang=self.lang_id.code)
        translated_values = {}

        model = self.type_import
        model_obj = self.env[model_data['model']].with_context(from_import=True)

        # res_object correspond à l'élément déjà existant en base de données, le cas échéant
        # cette variable sera renseignée à l'import du champ primaire de l'objet
        res_object = model_obj

        label_ref = f"ref. {line.get(model_data['reference_field'] or model_data['primary_field'] or 'name', '')}"

        # PARCOURS DE TOUS LES CHAMPS DE L'ENREGISTREMENT

        # Champs à importer (pour envoi à fonction create ou write)
        values = {}
        defaults = self._pre_compute_line(model_data)

        # Parcours de tous les champs de la ligne
        for file_field in file_fields:
            # Pour import articles, champ price est le coût d'achat à mettre dans le prix fournisseur.
            # On l'ignore car sera récupéré avec le champ seller_ids (fournisseur), voir plus bas.
            # Note : Normalement, le prix d'achat ne devrait pas être importé.
            #        Le seul champ importé devrait être le prix public hors taxe.
            #        Le prix d'achat devrait être calculé automatiquement avec la remise configurée côté client.
            if model == 'product.template' and file_field == 'price':
                continue

            # Si le nom du champ contient un champ relation c'est à dire se terminant par /nom_du_champ on l'enlève.
            file_field_norel = file_field[
                : file_field.rfind('/') if file_field.rfind('/') != -1 else len(file_field)
            ].strip()

            # On ne récupère que les champs du fichier d'import qui sont des champs de l'objet
            # (on ignore les champs inconnus du fichier d'import).
            if file_field_norel in fields_odoo:
                if isinstance(line[file_field], str) and line[file_field].lower() == "#empty":
                    line[file_field] = "#empty"

                #
                # VÉRIFICATION DE L'INTÉGRITÉ DE LA VALEUR DES CHAMPS
                # POUR LES CRITÈRES QUI NE DÉPENDENT PAS DU TYPE DU CHAMP
                #

                # si le champ est requis, vérification qu'il est renseigné
                if fields_odoo[file_field_norel]['required'] and (
                    line[file_field] == "#empty" or (line[file_field] == "" and not values.get(file_field_norel))
                ):
                    add_error(
                        _(
                            "line %(i)s : field %(field)s (%(file_field)s) empty but required. %(model)s not imported",
                            i=i,
                            field=fields_odoo[file_field_norel]['description'],
                            file_field=file_field,
                            model=model_data['object_name'].capitalize(),
                        )
                    )

                # Si le champ relation est un id, vérification qu'est un entier
                if fields_odoo[file_field_norel]['relation_field'] == 'id':
                    try:
                        int(line[file_field])
                    except ValueError:
                        add_error(
                            _(
                                "line %(i)s : field %(field)s (%(file_field)s) is not an id (integer) but the relation "
                                "field (after the /) is an id. %(model)s not imported",
                                i=i,
                                field=fields_odoo[file_field_norel]['description'],
                                file_field=file_field,
                                model=model_data['object_name'].capitalize(),
                            )
                        )

                #
                # FORMATAGE ET VÉRIFICATION DE L'INTÉGRITÉ DE LA VALEUR DES CHAMPS
                # POUR LES CRITÈRES QUI DÉPENDENT DU TYPE DU CHAMP
                #

                # Si est un float
                if fields_odoo[file_field_norel]['type'] == 'float':
                    message = self._process_float_field(
                        line, file_field, file_field_norel, fields_odoo, i, model_data, values
                    )
                    if message:
                        add_error(message)
                # Si est un field selection
                elif fields_odoo[file_field_norel]['type'] == 'selection':
                    # C'est un champ sélection. On vérifie que les données sont autorisées.
                    message = self._process_selection_field(
                        model, line, file_field, file_field_norel, fields_odoo, i, model_data, values
                    )
                    if message:
                        add_error(message)
                # Si est un boolean
                elif fields_odoo[file_field_norel]['type'] == 'boolean':
                    message = self._process_boolean_field(
                        line, file_field, file_field_norel, fields_odoo, i, model_data, values
                    )
                    if message:
                        add_error(message)
                # si est un many2one
                elif fields_odoo[file_field_norel]['type'] == 'many2one':
                    message = self._process_many2one_field(
                        model,
                        res_object,
                        simulate,
                        line,
                        file_field,
                        file_field_norel,
                        fields_odoo,
                        i,
                        model_data,
                        values,
                    )
                    if message:
                        add_error(message)
                # Si est un one2many
                elif fields_odoo[file_field_norel]['type'] == 'one2many':
                    # Cas des fournisseurs pour les produits. Il y a un objet intermédiaire avec un enregistrement
                    # pour chaque produit.
                    # On crée le fournisseur dans cet objet en renseignant le prix d'achat
                    if model == 'product.template' and file_field == 'seller_ids' and values.get('brand_id'):
                        if not line[file_field]:
                            continue
                        message = self._process_one2many_field(
                            line,
                            file_field,
                            file_field_norel,
                            fields_odoo,
                            i,
                            model_data,
                            values,
                        )
                        if message:
                            add_error(message)

                # Si est un many2many
                elif fields_odoo[file_field_norel]['type'] == 'many2many':
                    # C'est un many2many
                    # Ça équivaut à des étiquettes. On peut en importer plusieurs en les séparant par des virgules.
                    # Ex : étiquette1, étiquette2, étiquette3
                    message = self._process_many2many_field(
                        line, file_field, file_field_norel, fields_odoo, i, model_data, values
                    )
                    if message:
                        add_error(message)

                # Pour tous les autres types de champ (char, text, date, ...)
                # On ne fait que prendre sa valeur sans traitement particulier
                else:
                    # La gestion des traductions de champs se fera à part
                    label_ref, message = self._process_other_fields(
                        label_ref,
                        model,
                        res_object,
                        translated_values,
                        line,
                        file_field,
                        file_field_norel,
                        fields_odoo,
                        i,
                        model_data,
                        values,
                    )
                    if message:
                        add_error(message)

            if file_field and file_field_norel == model_data['primary_field']:
                # Récupération si possible de la valeur finale (par ex. si préfixe ajouté),
                # sinon de la valeur dans le fichier (si champ non importable)
                value = values.get(file_field_norel, line[file_field])

                # Si la référence est un champ vide, on ne s'arrête pas, ça sera une création,
                #   mais on garde une copie des lines pour faire un message d'avertissement.
                if value and value in duplicates:
                    if model == 'product.pack.line':
                        # L'import des composants de ce kit a déjà commencé.
                        # Les doublons sont les composants additionnels, ils ne génèrent pas d'erreur.
                        continue
                    code = IMPORT_WARNING_CODE
                    if not simulate:
                        break

                # On regarde si l'enregistrement existe déjà dans la base
                domain = [(model_data['primary_field'], '=', value)]
                if model == 'product.template':
                    # Pour un article, la clef est le champ primaire ET la marque.
                    # Un article sans marque (créé avant l'installation du module of_product_brand)
                    # est également valide.
                    if brand_id := values.get('brand_id') or defaults.get('brand_id'):
                        domain += ['|', ('brand_id', '=', False), ('brand_id', '=', brand_id)]
                    else:
                        domain += [('brand_id', '=', False)]
                res_object = model_obj.with_context(active_test=False).search(domain)

                if model == 'product.pack.line' and res_object:
                    if not simulate:
                        # On est en train d'importer le premier composant de ce kit, mais certains composants
                        # étaient déjà renseignés : on les supprime
                        res_object.unlink()
                    # Dans tous les cas on vide res_object pour ne pas considérer qu'il s'agit d'une mise à jour
                    # mais bien d'une création de line de composants.
                    res_object = model_obj
                    continue

                if model == 'product.template' and len(res_object) > 1:
                    # Plusieurs articles trouvés, recherche sur la marque
                    res_object = res_object.filtered('brand_id') or res_object

                if len(res_object) > 1:
                    # Il existe plusieurs articles dans la base avec cette référence.
                    # On ne sait pas lequel mettre à jour. On passe au suivant en générant une erreur.
                    add_error(
                        _(
                            "line %(i)s : %(model)s with reference %(ref)s has multiples matches in the database, "
                            "impossible to know which one to update. %(model)s not imported.",
                            i=i,
                            model=model_data['object_name'].capitalize(),
                            ref=label_ref,
                        )
                    )

                    # Afin de continuer la simulation d'import correctement,
                    # on prend arbitrairement un des objets disponibles
                    # Evite notamment des erreurs pour la simulation d'import d'articles,
                    # car l'objet contient des paramètres d'import
                    res_object = res_object[0]

                if not res_object:
                    # Il s'agit d'une création, on applique donc les valeurs par défaut.
                    for key, val in defaults.items():
                        values.setdefault(key, val)

        try:
            # Champs à importer (pour envoi à fonction create ou write)
            self._post_compute_line(file_fields, res_object, values)
        except OfImportError as e:
            add_error(
                _(
                    "line %(i)s : %(e_name)s %(model)s not imported.",
                    i=i,
                    e_name=e.args[0],
                    model=model_data['object_name'].capitalize(),
                )
            )

        if not res_object and code != IMPORT_WARNING_CODE:
            # En cas de création, on doit vérifier que tous les champs Odoo requis ont bien été renseignés.
            for key in fields_odoo:
                if fields_odoo[key]['required'] is True and key not in values:
                    add_error(
                        _(
                            "line %(i)s : field %(field)s (%(key)s) required but not present in the import file. "
                            "%(model)s not imported.",
                            i=i,
                            field=fields_odoo[key]['description'],
                            key=key,
                            model=model_data['object_name'].capitalize(),
                        )
                    )

        messages = import_errors
        if messages:
            code = IMPORT_ERROR_CODE
        if not (messages or code == IMPORT_WARNING_CODE):
            if res_object:
                # Il y a un (et un seul) enregistrement dans la base avec cette référence. On le met à jour.
                try:
                    if not simulate:
                        # Pour gérer les traductions, on importe d'abord avec la langue par défaut (en_US),
                        # puis on met à jour les champs pour chaque valeur traduite importée.
                        res_object.with_context(lang='en_US').write(values)
                        for lang, vals in translated_values.items():
                            res_object.with_context(lang=lang).write(vals)
                    code = IMPORT_MODIFICATION_CODE
                    messages = [
                        Command.create(
                            {
                                'type': 'info',
                                'message': _(
                                    "Update %(model_name)s %(label_ref)s (line %(i)s)",
                                    model_name=model_data['object_name'],
                                    label_ref=label_ref,
                                    i=i,
                                ),
                            },
                        )
                    ]
                except Exception as exp:
                    code = IMPORT_ERROR_CODE
                    messages = [
                        Command.create(
                            {
                                'type': 'error',
                                'message': _(
                                    "line %(i)s : update failed %(model_name)s %(label_ref)s - Error : %(exp)s",
                                    i=i,
                                    model_name=model_data['object_name'],
                                    label_ref=label_ref,
                                    exp=exp,
                                ),
                            },
                        )
                    ]
            else:
                # L'enregistrement n'existe pas dans la base, on l'importe (création)
                try:
                    if not simulate:
                        # Pour améliorer les performances ,on désactive le logging dans mail.message
                        # Pour gérer les traductions, on importe d'abord avec la langue par défaut (en_US),
                        # puis on met à jour les champs pour chaque valeur traduite importée.
                        res_object = model_obj.with_context(
                            mail_create_nolog=True, mail_create_nosubscribe=True, mail_notrack=True, lang='en_US'
                        ).create(values)
                        for lang, vals in translated_values.items():
                            res_object.with_context(lang=lang).write(vals)
                    code = IMPORT_CREATION_CODE
                    messages = [
                        Command.create(
                            {
                                'type': 'info',
                                'message': _(
                                    "Creation %(model_name)s %(label_ref)s (line %(i)s)",
                                    model_name=model_data['object_name'],
                                    label_ref=label_ref,
                                    i=i,
                                ),
                            },
                        )
                    ]
                except Exception as exp:
                    code = IMPORT_ERROR_CODE
                    messages = [
                        Command.create(
                            {
                                'type': 'error',
                                'message': _(
                                    "line %(i)s : creation failed %(model_name)s %(label_ref)s - Error : %(exp)s",
                                    i=i,
                                    model_name=model_data['object_name'],
                                    label_ref=label_ref,
                                    exp=exp,
                                ),
                            },
                        )
                    ]

        if (simulate or code != IMPORT_ERROR_CODE) and model_data['primary_field'] in values:
            ref = values[model_data['primary_field']]
            if ref in duplicates:
                duplicates[ref][0] += 1
                duplicates[ref][1] += f", {i}"
            else:
                duplicates[ref] = [1, str(i)]

        if not simulate:
            if code == IMPORT_ERROR_CODE:
                # Si l'erreur est de type SQL, le cursor est en 'ABORT STATE' et commit() et rollback()
                #   ont le même effet.
                # En revanche, si l'erreur est une erreur python, le cursor est correct et un commit()
                #   risque de valider un import incomplet.
                self._cr.rollback()
            else:
                self._cr.commit()
        return code, messages

    def action_import_line_attachment(self, line, file_fields, fields_odoo, i, model_data, duplicates, simulate):
        attachment_obj = self.env['ir.attachment']
        import_errors = []
        code = IMPORT_CREATION_CODE

        def add_error(msg):
            if msg:
                import_errors.append(Command.create({'type': 'error', 'message': msg}))
            if not simulate:  # not simulate, we raise the error
                raise OfImportError(import_errors)

        # clé d'unicité
        key = (line['res_id'], line['res_field'], not line['res_field'] and line['name'])
        if key in duplicates:
            duplicates[key][0] += 1
            duplicates[key][1] += f", {i}"
            return IMPORT_WARNING_CODE, ""
        else:
            duplicates[key] = [1, str(i)]

        allowed_paths = config.get('of_access_folders', '')
        allowed_paths = allowed_paths and allowed_paths.split(',') or []
        file_path = path.abspath(path.expanduser(path.expandvars(line['store_fname'])))
        value = ''
        try:
            if not any(file_path.startswith(p) for p in allowed_paths):
                add_error(
                    _(
                        "line %(i)s : You do not have right to access this file : %(file_path)s",
                        i=i,
                        file_path=file_path,
                    )
                )
                value = False
            else:
                value = open(file_path, 'rb').read()
                if not value:
                    add_error(_("line %(i)s : the file is empty : %(file_path)s", i=i, file_path=file_path))
        except (IOError, OSError):
            if path.exists(file_path):
                add_error(_("line %(i)s : impossible to open the file : %(file_path)s", i=i, file_path=file_path))
            else:
                add_error(_("line %(i)s : file not found : %(file_path)s", i=i, file_path=file_path))

        res_model = line.get('res_model', False)
        res_obj = res_name = False
        if res_model not in self.env:
            add_error(_("line %(i)s : model not recognize : %(res_model)s", i=i, res_model=line['res_model']))
        else:
            res_name = line.get('res_id', '')
            res_obj = self.env[res_model]
            res_obj_name_search = res_obj.with_context(active_test=False).name_search(res_name, operator='=', limit=2)
            if not res_obj_name_search:
                add_error(_("line %(i)s : no result found for : %(res_name)s", i=i, res_name=res_name))
            elif len(res_obj_name_search) > 1:
                add_error(_("line %(i)s : multiple results for : %(res_name)s", i=i, res_name=res_name))
            else:
                res_obj = res_obj.browse(res_obj_name_search[0][0])

        res_field = line.get('res_field') or False
        if res_field and res_obj is not False and res_field not in res_obj._fields:
            add_error(
                _(
                    "line %(i)s : field not found : %(res_model)s.%(res_field)s",
                    i=i,
                    res_model=res_model,
                    res_field=res_field,
                )
            )
        label_ref = f"ref. {line['res_model']} : {line['res_id']} - {line['name']}"

        attachment = False
        if len(res_obj) == 1 and not res_field:
            attachment = attachment_obj.search(
                [
                    ('name', '=', line['name']),
                    ('res_model', '=', res_model),
                    ('res_field', '=', False),
                    ('res_id', '=', res_obj.id),
                    ('type', '=', 'binary'),
                ],
                limit=2,
            )
            if len(attachment) > 1:
                add_error(
                    _(
                        "line %(i)s : multiple attachments found : %(res_model)s - %(res_name)s : %(line_name)s",
                        i=i,
                        res_model=res_model,
                        res_name=res_name,
                        line_name=line['name'],
                    )
                )

        messages = import_errors
        if messages:
            code = IMPORT_ERROR_CODE
        if code == IMPORT_CREATION_CODE and not simulate:
            if res_field:
                # Champ binaire d'un objet
                if res_obj[res_field]:
                    code = IMPORT_MODIFICATION_CODE
                try:
                    res_obj[res_field] = value
                    messages = [
                        Command.create(
                            {
                                'type': 'info',
                                'message': _(
                                    "Update of field %(res_field)s %(label_ref)s (line %(i)s)",
                                    i=i,
                                    res_field=res_field,
                                    label_ref=label_ref,
                                ),
                            }
                        )
                    ]
                except Exception as e:
                    code = IMPORT_ERROR_CODE
                    add_error(
                        _(
                            "line %(i)s : Update failed %(res_model)s %(label_ref)s - Error : %(e)s",
                            i=i,
                            res_model=res_model,
                            label_ref=label_ref,
                            e=e,
                        )
                    )

            elif attachment is not False:
                # Pièce jointe
                attachment_data = {
                    'name': line['name'],
                    'res_model': res_model,
                    'res_field': res_field,
                    'res_id': res_obj.id,
                    'type': 'binary',
                    'datas': base64.b64encode(value),
                }
                try:
                    if attachment:
                        attachment.write(attachment_data)
                        code = IMPORT_MODIFICATION_CODE
                        messages = [
                            Command.create(
                                {
                                    'type': 'info',
                                    'message': _(
                                        "Update attachment %(label_ref)s (line %(i)s)", label_ref=label_ref, i=i
                                    ),
                                }
                            )
                        ]
                    else:
                        attachment_obj.create(attachment_data)
                        code = IMPORT_CREATION_CODE
                        messages = [
                            Command.create(
                                {
                                    'type': 'info',
                                    'message': _(
                                        "Create attachment %(label_ref)s (line %(i)s)", label_ref=label_ref, i=i
                                    ),
                                }
                            )
                        ]
                except Exception as e:
                    code = IMPORT_ERROR_CODE
                    add_error(
                        _(
                            "line %(i)s : %(mode)s %(res_model)s %(label_ref)s - Error : %(e)s",
                            i=i,
                            mode=attachment and _("update failed") or _("creation failed"),
                            res_model=res_model,
                            label_ref=label_ref,
                            e=e,
                        )
                    )

        if not simulate:
            if code == IMPORT_ERROR_CODE:
                # Si l'erreur est de type SQL, le cursor est en 'ABORT STATE' et commit() et rollback()
                #   ont le même effet.
                # En revanche, si l'erreur est une erreur python, le cursor est correct et un commit()
                #   risque de valider un import incomplet.
                self._cr.rollback()
            else:
                self._cr.commit()
        return code, messages

    def action_import(self, simulate=True):
        # VARIABLES DE CONFIGURATION

        frequence_commit = 100  # Enregistrer (commit) tous les n enregistrements

        model = self.type_import  # On récupère l'objet (model) à importer indiqué dans le champ type d'import

        model_data = self._get_model_data()[model]
        model_data['model'] = model

        # Initialisation variables

        # On récupère la liste des champs de l'objet (depuis ir.model.fields)
        fields_odoo = self._get_odoo_fields(model, self.lang_id.code or self.env.lang)
        date_start = time.strftime('%Y-%m-%d %H:%M:%S')

        self.import_success_ids.unlink()
        self.import_warning_ids.unlink()
        self.import_error_ids.unlink()

        import_success = []
        import_warnings = []
        import_errors = []

        if simulate:
            import_success += [
                Command.create({'type': 'info', 'message': _("SIMULATION - nothing have been create/update.")})
            ]
            import_warnings += [
                Command.create({'type': 'warning', 'message': _("SIMULATION - nothing have been create/update.")})
            ]
            import_errors += [
                Command.create({'type': 'error', 'message': _("SIMULATION - nothing have been create/update.")})
            ]

        total_count = 0
        added_count = 0
        updated_count = 0
        failed_count = 0
        ignored_count = 0
        error = 0

        # LECTURE DU FICHIER D'IMPORT SELON EXTENSION (CHOISIR READER)
        # Le reader doit :
        # - Au premier appel, retourner la liste des noms des colonnes
        # - Aux appels suivants, retourner un dictionnaire clef:valeur de la prochaine ligne non vide
        #   ou lever une exception de type StopIteration
        # - S'assurer que chacune des valeurs retournées a subi un strip()
        reader = self._choose_reader()

        # ANALYSE DES CHAMPS DU FICHIER D'IMPORT

        # On récupère la 1ère ligne du fichier (liste des champs) pour vérifier si des champs existent en
        # plusieurs exemplaires
        file_fields = next(reader)

        if model == 'product.template':
            # Définition de l'ordre de lecture des champs. La marque doit être lue en premier
            file_fields = sorted(
                file_fields,
                key=lambda field: (
                    (field.split('/')[0] == 'brand_id' and 10)
                    or (field == model_data['reference_field'] and 20)
                    or (field == model_data['primary_field'] and 30)
                    or 40
                ),
            )

            # L'import de tarif nécessite l'existence de la marque associée aux articles
            if self.prefix:
                if default_brand := self.env['of.product.brand'].search([('code', '=', self.prefix.rstrip('_'))]):
                    model_data['default_brand_id'] = default_brand.id
                    if default_brand.partner_id:
                        model_data['default_seller_ids'] = [
                            Command.clear(),
                            Command.create({'partner_id': default_brand.partner_id.id}),
                        ]
                else:
                    error = 1
                    import_errors += [
                        Command.create(
                            {
                                'type': 'error',
                                'message': _("No brand correspond to the prefix %s.") % self.prefix,
                            }
                        )
                    ]
            else:
                for file_field in file_fields:
                    relation_field = file_field.split('/')[0]
                    if relation_field == 'brand_id':
                        break
                else:
                    import_errors += [
                        Command.create(
                            {
                                'type': 'info',
                                'message': _(
                                    "A prefix must be choose for the import, or a column in the file must "
                                    "define the product brand"
                                ),
                            },
                        )
                    ]

            # Les udm des articles seront nécessaires pour le calcul des prix de revient et de vente
            for key, val in self.env['product.template'].default_get(('uom_id', 'uom_po_id')).items():
                model_data[f'default_{key}'] = val

            # L'import de tarif est susceptible d'ajouter des lignes de configuration dans les marques.
            # On sauvegarde l'état actuel pour récupérer les lignes nouvellement créées
            product_categ_config_obj = self.env['of.import.product.categ.config']
            product_categ_config_ids = product_categ_config_obj.search([]).ids
        else:
            # Définition de l'ordre de lecture des champs. La marque doit être lue en premier
            file_fields = sorted(
                file_fields,
                key=lambda field: (
                    (field == model_data['reference_field'] and 10)
                    or (field.split('/')[0] == model_data['primary_field'] and 20)
                    or 30
                ),
            )

        # Vérification si le champ primaire est bien dans le fichier d'import (si le champ primaire est défini)
        file_fields_racine = [field.split('/')[0] for field in file_fields]
        if model_data['primary_field'] and model_data['primary_field'] not in file_fields_racine:
            error = 1
            import_errors += [
                Command.create(
                    {
                        'type': 'error',
                        'message': _(
                            "The reference field which is needed to identify a %(model_name)s (%(primary_field)s) "
                            "is not in the import file ",
                            model_name=model_data['object_name'],
                            primary_field=model_data['primary_field'],
                        ),
                    },
                )
            ]

        # Vérification si il y a des champs du fichier d'import qui sont en plusieurs exemplaires et détection
        # champ relation (id, id externe, nom)
        duplicates = {}

        for file_field in file_fields:
            # Récupération du champ relation si est indiqué (dans le nom du champ après un /)
            relation_field = file_field[file_field.rfind('/') + 1 or len(file_field) :].strip()

            if relation_field:
                # On le retire du nom du champ.
                file_field = file_field[: -len(relation_field) - 1].strip()

            if file_field in duplicates:
                duplicates[file_field] = duplicates[file_field] + 1
            else:
                duplicates[file_field] = 1

            # Test si est un champ de l'objet (sinon message d'information que le champ est ignoré à l'import)
            if file_field not in fields_odoo:
                import_warnings += [
                    Command.create(
                        {
                            'type': 'warning',
                            'message': _(
                                "Info : column \"%s\" in the import file is not recognize. Ignored during the import."
                            )
                            % file_field,
                        },
                    )
                ]
            else:
                # Vérification que le champ relation (si est indiqué) est correct.
                if (
                    relation_field
                    and fields_odoo[file_field]['type'] in ('many2one',)
                    and not fields_odoo[file_field]['relation_field']
                ):
                    if not self.env['ir.model.fields'].search(
                        [('model', '=', fields_odoo[file_field]['relation']), ('name', '=', relation_field)]
                    ):
                        import_errors += [
                            Command.create(
                                {
                                    'type': 'error',
                                    'message': _(
                                        "The relation field %(relation_field)s (after the /) in the "
                                        "column %(file_field)s does not exist.",
                                        relation_field=relation_field,
                                        file_field=file_field,
                                    ),
                                },
                            )
                        ]
                        error = 1
                    else:
                        fields_odoo[file_field]['relation_field'] = relation_field
                elif relation_field:
                    import_errors += [
                        Command.create(
                            {
                                'type': 'error',
                                'message': _(
                                    "a relation field (after the /) in the column %s is not possible " "for this field"
                                )
                                % file_field,
                            },
                        )
                    ]
                    error = 1

        for file_field in duplicates:
            # On affiche un message d'avertissement si le champ existe en plusieurs exemplaires et si c'est un champ
            # connu à importer
            if file_field in fields_odoo and duplicates[file_field] > 1:
                import_errors += [
                    Command.create(
                        {
                            'type': 'error',
                            'message': _(
                                "The column %(file_field)s in the import file exist %(duplicates)s times",
                                file_field=file_field,
                                duplicates=duplicates[file_field],
                            ),
                        },
                    )
                ]
                error = 1

        if error:  # On arrête si erreur
            self.write(
                {
                    'total_count': total_count,
                    'added_count': added_count,
                    'updated_count': updated_count,
                    'failed_count': failed_count,
                    'ignored_count': ignored_count,
                    'import_success_ids': import_success,
                    'import_warning_ids': import_warnings,
                    'import_error_ids': import_errors,
                }
            )
            return

        # On ajoute le séparateur (caractère souligné) entre le préfixe et la référence si il n'a pas déjà été mis.
        prefix = self.prefix and self.prefix.encode("utf-8") or ''
        if prefix and prefix[-1:] != '_':
            prefix = prefix + '_'

        duplicates = {}  # Variable pour test si enregistrement en plusieurs exemplaires dans fichier d'import
        i = 1  # No de ligne

        #
        # IMPORT ENREGISTREMENT PAR ENREGISTREMENT
        #

        fct_import_line = self.action_import_line
        if model == 'ir.attachment':
            fct_import_line = self.action_import_line_attachment
        # On parcourt le fichier enregistrement par enregistrement
        while True:
            try:
                line = next(reader)
            except StopIteration:
                break

            if (total_count + 1) % frequence_commit == 0:
                if model == 'product.template':
                    product_categ_configs = product_categ_config_obj.search(
                        [('id', 'not in', product_categ_config_ids)], order='brand_id, categ_origin'
                    )
                    if product_categ_configs:
                        for conf in product_categ_configs:
                            import_warnings += [
                                Command.create(
                                    {
                                        'type': 'warning',
                                        'message': _(
                                            "Brand %(brand_name)s : Add configuration for the "
                                            "category %(categ_origin)s",
                                            brand_name=conf.brand_id.name,
                                            categ_origin=conf.categ_origin,
                                        ),
                                    },
                                )
                            ]
                self.write(
                    {
                        'total_count': total_count,
                        'added_count': added_count,
                        'updated_count': updated_count,
                        'failed_count': failed_count,
                        'ignored_count': ignored_count,
                        'import_success_ids': import_success,
                        'import_warning_ids': import_warnings,
                        'import_error_ids': import_errors,
                    }
                )

                import_success = []
                import_warnings = []
                import_errors = []

            i = i + 1
            total_count += 1

            try:
                code, messages = fct_import_line(line, file_fields, fields_odoo, i, model_data, duplicates, simulate)

                if messages:
                    if code == IMPORT_ERROR_CODE:
                        import_errors += messages
                    else:
                        import_success += messages
            except OfImportError as e:
                code = IMPORT_ERROR_CODE
                import_errors += e.args[0]

            if code == IMPORT_ERROR_CODE:
                failed_count += 1
            elif code == IMPORT_WARNING_CODE:
                ignored_count += 1
            elif code == IMPORT_CREATION_CODE:
                added_count += 1
            elif code == IMPORT_MODIFICATION_CODE:
                updated_count += 1

        if model == 'product.pack.line':
            # Les "doublons" ne génèrent pas de warning pour les kits car il s'agit de différents
            # composants d'un même kit.
            duplicates = {}

        # On affiche les enregistrements qui étaient en plusieurs exemplaires dans le fichier d'import.
        for key in duplicates:
            if key == "":
                import_warnings += [
                    Command.create(
                        {
                            'type': 'warning',
                            'message': _(
                                "WARNING : this records have been create but have an empty reference field "
                                "(duplicates possible in case of multiple import : line(s) %s)."
                            )
                            % duplicates[key][1],
                        },
                    )
                ]
            elif duplicates[key][0] > 1:
                import_warnings += [
                    Command.create(
                        {
                            'type': 'warning',
                            'message': _(
                                "%(model_name)s ref. %(key)s exist %(duplicates)s times in the import file "
                                "(lines %(lines)s). Only the first one is imported.",
                                model_name=model_data['object_name'],
                                key=key,
                                duplicates=duplicates[key][0],
                                lines=duplicates[key][1],
                            ),
                        },
                    )
                ]

        # On enregistre les dernières lignes qui ne l'auraient pas été.
        if model == 'product.template':
            product_categ_configs = product_categ_config_obj.search(
                [('id', 'not in', product_categ_config_ids)], order='brand_id, categ_origin'
            )
            if product_categ_configs:
                for conf in product_categ_configs:
                    import_warnings += [
                        Command.create(
                            {
                                'type': 'warning',
                                'message': _(
                                    "Brand %(brand_name)s : Add configuration for the category "
                                    "%(categ_origin)s (%(match)s)",
                                    brand_name=conf.brand_id.name,
                                    categ_origin=conf.categ_origin,
                                    match=conf.of_import_categ_id and _('with match') or _('without match'),
                                ),
                            },
                        )
                    ]
        self.write(
            {
                'total_count': total_count,
                'added_count': added_count,
                'updated_count': updated_count,
                'failed_count': failed_count,
                'ignored_count': ignored_count,
                'import_success_ids': import_success,
                'import_warning_ids': import_warnings,
                'import_error_ids': import_errors,
                'date_start_import': date_start,
                'date_end_import': time.strftime('%Y-%m-%d %H:%M:%S'),
            }
        )

        if not simulate:
            self.write({'state': 'imported'})

        return

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    def _get_model_data(self):
        """
        Returns a dictionary containing model data.

        The dictionary maps model names to a sub-dictionary containing the following information:
        - 'object_name': The display name of the object.
        - 'primary_field': The field used to detect if a record already exists (for update) or is new (for creation).
        - 'reference_field': The field that contains the reference for adding a prefix.

        :return: A dictionary containing model data.
        """
        return {
            'product.template': {
                'object_name': "Product",
                'primary_field': 'default_code',
                'reference_field': 'default_code',
            },
            'ir.attachment': {
                'object_name': "Image/Attachment",
                # Champ inutile pour les pièces jointes : les doublons se gèrent avec une clef sur plusieurs champs.
                'primary_field': 'name',
                'reference_field': '',
            },
            'product.pack.line': {
                'object_name': "Packs components",
                # Dans le cas des composants de kits, le champ primaire est le kit.
                # Cela permet de détourner la gestion des doublons : la première fois que la
                # clef primaire est détectée, on vide les anciens composants du kit.
                'primary_field': 'parent_product_id',
                'reference_field': '',
            },
            'res.partner': {
                'object_name': "Partner",
                'primary_field': 'ref',
                'reference_field': 'ref',
                # 2 champs suivants : on récupère les id des types de compte comptable payable et recevable
                # pour création comptes comptables clients et fournisseurs (généralement 411 et 401).
                'data_account_type_receivable_id': self.env['ir.model.data'].check_object_reference(
                    'account', 'field_res_partner__property_account_receivable_id'
                )[1],
                'data_account_type_payable_id': self.env['ir.model.data'].check_object_reference(
                    'account', 'field_res_partner__property_account_payable_id'
                )[1],
            },
            'of.service.request': {
                'object_name': "Service request",
                'primary_field': 'id',
                'reference_field': '',
            },
            'res.partner.bank': {
                'object_name': "Partner bank account",
                'primary_field': 'acc_number',
                'reference_field': '',
            },
            'crm.lead': {
                'object_name': "Partner/Opportunity",
                'primary_field': 'of_ref',
                'reference_field': 'of_ref',
            },
        }

    @api.model
    def _get_odoo_fields(self, model=None, lang=False):
        """Returns a dictionary containing the characteristics of Odoo fields based on the selected import type
        (field type_import).

        :param model: The model for which to retrieve the field characteristics.
        :param lang: The language in which to retrieve the field characteristics.

        :returns: A dictionary containing the field characteristics.
        """
        if not model:
            return {}
        if model == 'ir.attachment':
            return _get_odoo_fields_attachment()

        fields_odoo = {}

        langs = self.env['res.lang'].search([('active', '=', True)]).mapped('code')
        if len(langs) == 1:
            # If there is only one active language, Odoo does not handle translations.
            langs = []
        else:
            langs = [lan for lan in langs if lan not in ['en_US', lang]]

        # Retrieve the list of fields from fields_get.
        fields_definition = self.env[model].fields_get(
            attributes=['field_description', 'required', 'type', 'relation', 'relation_field', 'translate', 'string']
        )
        for f in fields_definition:
            field = self.env[model]._fields[f]
            if field.compute and not field.inverse and field.readonly:
                continue

            if not field.store:
                continue
            fields_odoo[f] = {
                'description': fields_definition[f].get('string'),
                'required': fields_definition[f].get('required'),
                'type': fields_definition[f].get('type'),
                'relation': fields_definition[f].get('relation'),
                'relation_field': fields_definition[f].get('relation_field'),
                'lang': False,
                'translate': fields_definition[f].get('translate'),
            }

            if fields_definition[f].get('translate'):
                for lan in langs:
                    fields_odoo[f"[{lan}]{f}"] = {
                        'description': fields_definition[f].get('string'),
                        'required': False,
                        'type': fields_definition[f].get('type'),
                        'relation': fields_definition[f].get('relation'),
                        'relation_field': fields_definition[f].get('relation_field'),
                        'lang': lan,
                        'translate': False,
                    }

        # Fields that are required can have a default value
        # (so ultimately there is no obligation to fill them in).
        # Retrieve the fields that have a default value and indicate that they are not required.
        fields_required = [key for key, vals in fields_odoo.items() if vals['required']]
        for key, val in self.env[model].default_get(fields_required).items():
            fields_odoo[key]['required'] = val is False

        # Manually marking a field as required is not necessary if it is marked as required by Odoo's create function.
        if model == 'product.template':
            if 'product_variant_ids' in fields_odoo:
                fields_odoo['product_variant_ids']['required'] = False

            if 'brand_id' in fields_odoo:
                # In the case of price import, the brand of the article must be provided
                fields_odoo['brand_id']['required'] = True

            if 'categ_id' in fields_odoo:
                # The imported categ_id is the supplier's category.
                # The actual categ_id will be calculated based on the brand
                fields_odoo['categ_id']['required'] = False

        if model == 'product.pack.line' and 'product_uom_id' in fields_odoo:
            fields_odoo['product_uom_id']['required'] = False
        return fields_odoo

    def _choose_reader(self):
        """Chooses the appropriate reader based on the file type."""
        if self.file:
            if self.file_type == 'xls':
                return _read_xls(self.file)
            elif self.file_type == 'xlsx':
                return _read_xlsx(self.file)
            elif self.file_type == 'csv':
                return _read_csv(self.file, self.separator)
            else:
                raise UserError(_("Unrecognized file type"))

    def _pre_compute_line(self, model_data):
        """Pre-computes the line by extracting values from the model_data dictionary."""
        return {key[8:]: val for key, val in model_data.items() if key.startswith('default_')}

    def _post_compute_line(self, file_fields, res_object, values):
        """Post-computes the line by applying the post-computation to the values.

        :param file_fields: list of fields in the file
        :param res_object: the object to import
        :param values: dict of values on which to apply the post-computation
        """
        if self.type_import == 'product.template':
            self._post_compute_product_template(file_fields, res_object, values)

        elif self.type_import == 'product.pack.line':
            self._post_compute_product_pack_line(values)

    def _post_compute_product_pack_line(self, values):
        """
        Perform post-computation for product pack line.

        :param values: A dictionary containing the values for the product pack line.
        """
        return values

    def _post_compute_product_template(self, file_fields, res_object, values):
        """
        Perform post-computation operations for the product template.

        This method is responsible for setting the 'categ_id' value in the 'values' dictionary and for
        computing the purchase and sale prices based on the values in the 'values' dictionary.

        :param file_fields: list of fields in the file
        :param res_object: the product template object being processed
        :param values: dict of values on which to apply the post-computation
        """
        uom_obj = self.env['uom.uom']
        if brand_id := values.get('brand_id'):
            brand = self.env['of.product.brand'].browse(brand_id)
        else:
            brand = res_object.brand_id
            # Si brand n'est pas défini, une exception sera automatiquement générée plus tard
            # car la marque est un champ obligatoire pour l'import de tarif

        supplier_categ = values.get(
            'of_seller_product_category_name', res_object and res_object.of_seller_product_category_name or ''
        )
        if 'categ_id' in file_fields and 'categ_id' not in values:
            # Si la catégorie d'article n'est pas renseignée, on prend la catégorie par défaut de la marque
            values['categ_id'] = brand.compute_product_categ(supplier_categ, product=res_object).id

        # Calcul des prix d'achat/vente en fonction des règles de calcul et du prix public ht
        if 'list_price' in values and brand:
            values.setdefault('of_seller_pp_untaxed', values['list_price'])
            misc_val_fields = (
                'of_misc_costs',
                'of_misc_taxes',
                'of_other_logistic_costs',
                'of_purchase_transport',
                'of_sale_coeff',
                'of_sale_transport',
            )
            values.update(
                brand.compute_product_price(
                    values['of_seller_pp_untaxed'],
                    supplier_categ,
                    uom_obj.browse(values.get('uom_id', res_object.uom_id.id)),
                    uom_obj.browse(values.get('uom_po_id', res_object.uom_po_id.id)),
                    product=res_object,
                    price=values.get('of_seller_price'),
                    discount=values.get('of_seller_discount'),
                    cost=values.pop('standard_price', 0),
                    based_on_price=values.get('of_is_net_price'),
                    other_vals={key: values.get(key, 0) for key in misc_val_fields if key in file_fields},
                )
            )

    def _process_float_field(self, line, file_field, file_field_norel, fields_odoo, i, model_data, values):
        """
        Process a float field in the import file.

        Args:
            line (dict): The current line being processed from the import file.
            file_field (str): The name of the field in the import file.
            file_field_norel (str): The name of the field in the Odoo model.
            fields_odoo (dict): A dictionary containing information about the Odoo model fields.
            i (int): The line number being processed.
            model_data (dict): A dictionary containing information about the Odoo model.
            values (dict): A dictionary containing the processed values for the Odoo model.

        Returns:
            None if the field is processed successfully, otherwise an error message.

        Raises:
            ValueError: If the value in the import file is not a valid float.

        """
        line[file_field] = str(line[file_field]).replace(',', '.')
        if line[file_field] != "":
            try:
                values[file_field_norel] = float(line[file_field])
            except ValueError:
                return _("line %(i)s : field %(field)s (%(file_field)s) is not a number. %(model)s not imported") % {
                    'i': i,
                    'field': fields_odoo[file_field_norel]['description'],
                    'file_field': file_field,
                    'model': model_data['object_name'].capitalize(),
                }
        return None

    def _process_selection_field(self, model, line, file_field, file_field_norel, fields_odoo, i, model_data, values):
        if line[file_field] not in dict(self.env[model]._fields[file_field].selection):
            return _(
                "line %(i)s : field %(field)s (%(file_field)s) value \"%(value)s\" not authorized. %(model)s"
                "not imported",
                i=i,
                field=fields_odoo[file_field_norel]['description'],
                file_field=file_field,
                value=line[file_field],
                model=model_data['object_name'].capitalize(),
            )
        else:
            values[file_field_norel] = line[file_field]
        return None

    def _process_boolean_field(self, line, file_field, file_field_norel, fields_odoo, i, model_data, values):
        """
        Process a boolean field from the input line and update the values dictionary.

        :param line: The input line dictionary.
        :param file_field: The name of the field in the input file.
        :param file_field_norel: The name of the field without relation in the input file.
        :param fields_odoo: A dictionary containing information about the Odoo model fields.
        :param i: The line number being processed.
        :param model_data: A dictionary containing information about the Odoo model.
        :param values: Dictionary to store the processed values.

        :return: None if the field is processed successfully, otherwise an error message.
        """
        if line[file_field].upper() in ('1', 'TRUE', 'VRAI'):
            values[file_field] = True
        elif line[file_field].upper() in ('0', 'FALSE', 'FAUX'):
            values[file_field] = False
        else:
            return _(
                "line %(i)s : field %(field)s (%(file_field)s) value \"%(value)s\" not authorized "
                "(only : 0, 1, True, False, vrai, faux). %(model)s not imported",
                i=i,
                field=fields_odoo[file_field_norel]['description'],
                file_field=file_field,
                value=line[file_field],
                model=model_data['object_name'].capitalize(),
            )
        return None

    def _process_many2one_field(
        self,
        model,
        res_object,
        simulate,
        line,
        file_field,
        file_field_norel,
        fields_odoo,
        i,
        model_data,
        values,
    ):
        """
        Process a Many2one field from the input line and update the values dictionary.

        :param model: The name of the model being imported.
        :param res_object: The object being imported.
        :param simulate: Flag indicating whether the import is being simulated.
        :param line: The current line being processed from the import file.
        :param file_field: The name of the field in the import file.
        :param file_field_norel: The name of the field in the Odoo model.
        :param fields_odoo: A dictionary containing information about the Odoo model fields.
        :param i: The line number being processed.
        :param model_data: A dictionary containing information about the Odoo model.
        :param values: Dictionary to store the processed values.

        :return: None if the field is processed successfully, otherwise an error message.
        """
        product_categ_obj = self.env['product.category']
        product_categ_config_obj = self.env['of.import.product.categ.config']
        if model == 'product.template' and file_field == 'categ_id':
            values['of_seller_product_category_name'] = line[file_field]
            if line[file_field] == '#empty':
                # Avoir une catégorie non renseignée côté fournisseur n'empêche pas de calculer celle
                # du distributeur grâce à la marque
                line[file_field] = '.'
                values['of_seller_product_category_name'] = ''
            elif line[file_field] == '':
                # A chaque import les informations fournisseur sont supprimées et re-générées.
                # Il faut dans ce cas les récupérer
                if res_object:
                    line[file_field] = '.'
                    values['of_seller_product_category_name'] = res_object.of_seller_product_category_name or ''
        if line[file_field] == "#empty" and not fields_odoo[file_field_norel]['required']:
            # Si le champ n'est pas obligatoire et qu'il est vide, on met une valeur vide.
            values[file_field_norel] = ""
        elif line[file_field] != "":
            found = False
            # Si import partenaires et si c'est le compte comptable client ou fournisseur,
            # on regarde si pointe sur un compte comptable existant
            if model == 'res.partner' and file_field == 'property_account_receivable_id':
                res_ids = (
                    self.env[fields_odoo[file_field_norel]['relation']]
                    .with_context(active_test=False)
                    .search([('code', '=', line[file_field]), ('internal_type', '=', 'receivable')])
                )
            elif model == 'res.partner' and file_field == 'property_account_payable_id':
                res_ids = (
                    self.env[fields_odoo[file_field_norel]['relation']]
                    .with_context(active_test=False)
                    .search([('code', '=', line[file_field]), ('internal_type', '=', 'payable')])
                )
            # Si import de produit, la catégorie de produit peut avoir une correspondance
            elif model == 'product.template' and file_field == 'categ_id':
                # Sauvegarde de la catégorie donnée par le fournisseur
                line[file_field] = values['of_seller_product_category_name']

                brand = values.get('brand_id') and self.env['of.product.brand'].browse(values['brand_id'])
                if res_object and not brand:
                    brand = res_object.brand_id

                if (
                    brand
                    and simulate
                    and not product_categ_config_obj.search(
                        [('brand_id', '=', brand.id), ('categ_origin', '=', line[file_field])]
                    )
                ):
                    # Lors d'une simulation, les catégories manquantes sont ajoutées à la configuration
                    # de la marque
                    categ = product_categ_obj.search([('name', '=', line[file_field])])
                    product_categ_config_obj.create(
                        {
                            'brand_id': brand.id,
                            'categ_origin': line[file_field],
                            'of_import_categ_id': categ and len(categ) == 1 and categ.id or False,
                        }
                    )

                if categ := brand and brand.compute_product_categ(line[file_field], product=res_object):
                    res_ids = categ
                else:
                    found = True
            else:
                found = True

            if found:
                if line[file_field] == "#empty":
                    res_ids = ""
                else:
                    res_ids = (
                        self.env[fields_odoo[file_field_norel]['relation']]
                        .with_context(active_test=False)
                        .search(
                            [
                                (
                                    fields_odoo[file_field_norel]['relation_field'] or 'name',
                                    '=',
                                    line[file_field],
                                )
                            ]
                        )
                    )

            if len(res_ids) == 1:
                values[file_field_norel] = res_ids.id
                # Le fournisseur est devenu un champ obligatoire de la marque.
                # Cette vérification pourra être retirée.
                if model == 'product.template' and file_field_norel == 'brand_id' and res_ids.partner_id:
                    values['seller_ids'] = [Command.clear(), Command.create({'partner_id': res_ids.partner_id.id})]
            elif len(res_ids) > 1:
                return _(
                    "line %(i)s : field %(field)s (%(file_field)s) value \"%(value)s\" has multiple matches. "
                    "%(model)s not imported.",
                    i=i,
                    field=fields_odoo[file_field_norel]['description'],
                    file_field=file_field,
                    value=line[file_field],
                    model=model_data['object_name'].capitalize(),
                )
            elif model == 'res.partner' and file_field == 'property_account_receivable_id' and 'name' in line:
                if not simulate:
                    values[file_field_norel] = self.env[fields_odoo[file_field_norel]['relation']].create(
                        {
                            'name': line['name'],
                            'code': line[file_field],
                            'reconcile': True,
                            'user_type_id': model_data['data_account_type_receivable_id'],
                        }
                    )
            elif model == 'res.partner' and file_field == 'property_account_payable_id' and 'name' in line:
                if not simulate:
                    values[file_field_norel] = self.env[fields_odoo[file_field_norel]['relation']].create(
                        {
                            'name': line['name'],
                            'code': line[file_field],
                            'reconcile': True,
                            'user_type_id': model_data['data_account_type_payable_id'],
                        }
                    )
            elif line[file_field] == "#empty":
                values[file_field_norel] = ''
            else:
                return _(
                    "line %(i)s : field %(field)s (%(file_field)s) value \"%(value)s\" has no match. %(model)s"
                    "not imported",
                    i=i,
                    field=fields_odoo[file_field_norel]['description'],
                    file_field=file_field,
                    value=line[file_field],
                    model=model_data['object_name'].capitalize(),
                )
        return None

    def _process_one2many_field(self, line, file_field, file_field_norel, fields_odoo, i, model_data, values):
        """
        Process a One2Many field from the input line and update the values dictionary.

        :param line: Dictionary representing the current line being processed.
        :param file_field: Name of the field in the import file.
        :param file_field_norel: Name of the field without relation in the import file.
        :param fields_odoo: Dictionary containing information about the Odoo fields.
        :param i: Line number being processed.
        :param model_data: Dictionary containing information about the model being imported.
        :param values: Dictionary to store the processed values.
        """
        brand = self.env['of.product.brand'].browse(values['brand_id'])
        if brand.partner_id:
            if brand.partner_id.name.strip() != line[file_field]:
                return _(
                    "line %(i)s : field %(field)s (%(file_field)s) the choosen supplier (%(value)s) does not match "
                    "the brand %(brand_name)s (%(partner_name)s). %(model)s not imported.",
                    i=i,
                    field=fields_odoo[file_field_norel]['description'],
                    file_field=file_field,
                    value=line[file_field],
                    brand_name=brand.name,
                    partner_name=brand.partner_id.name,
                    model=model_data['object_name'].capitalize(),
                )
        else:
            res_ids = self.env['res.partner'].search([('name', '=', line[file_field]), ('supplier', '=', True)])

            if len(res_ids) == 1:
                values[file_field_norel] = [Command.clear(), Command.create({'name': res_ids.id})]
            elif len(res_ids) > 1:
                return _(
                    "line %(i)s : field %(field)s (%(file_field)s) value \"%(value)s\" has multiple matches."
                    "%(model)s not imported.",
                    i=i,
                    field=fields_odoo[file_field_norel]['description'],
                    file_field=file_field,
                    value=line[file_field],
                    model=model_data['object_name'].capitalize(),
                )
            else:
                return _(
                    "line %(i)s : field %(field)s (%(file_field)s) value \"%(value)s\" has no match. %(model)s "
                    "not imported.",
                    i=i,
                    field=fields_odoo[file_field_norel]['description'],
                    file_field=file_field,
                    value=line[file_field],
                    model=model_data['object_name'].capitalize(),
                )
        return None

    def _process_many2many_field(self, line, file_field, file_field_norel, fields_odoo, i, model_data, values):
        """
        Process a Many2Many field from the input line and update the values dictionary.

        :param line: Dictionary representing the current line being processed.
        :param file_field: Name of the field in the import file.
        :param file_field_norel: Name of the field without relation in the import file.
        :param fields_odoo: Dictionary containing information about the Odoo fields.
        :param i: Line number being processed.
        :param model_data: Dictionary containing information about the model being imported.
        :param values: Dictionary to store the processed values.

        :return: True if the field was processed successfully, error message otherwise.
        """

        tag_ids = []
        if line[file_field] and line[file_field] != "#empty":
            # Il y a des données dans le champ d'import

            # On sépare les étiquettes quand il y a une virgule, puis on les parcourt
            line[file_field] = line[file_field].split(',')
            for tag in line[file_field]:
                # On regarde si l'étiquette existe.
                res_ids = (
                    self.env[fields_odoo[file_field_norel]['relation']]
                    .with_context(active_test=False)
                    .search([(fields_odoo[file_field_norel]['relation_field'] or 'name', '=', tag)])
                )
                if len(res_ids) == 1:
                    tag_ids.append(res_ids.id)
                elif len(res_ids) > 1:
                    return _(
                        "line %(i)s : field %(field)s (%(file_field)s) value \"%(tag)s\" has multiple matches. "
                        "%(model)s not imported.",
                        i=i,
                        field=fields_odoo[file_field_norel]['description'],
                        file_field=file_field,
                        tag=tag,
                        model=model_data['object_name'].capitalize(),
                    )
                else:
                    return _(
                        "line %(i)s : field %(field)s (%(file_field)s) value \"%(tag)s\" has no match. %(model)s "
                        "not imported.",
                        i=i,
                        field=fields_odoo[file_field_norel]['description'],
                        file_field=file_field,
                        tag=tag,
                        model=model_data['object_name'].capitalize(),
                    )
        if line[file_field] == "#empty":
            values[file_field_norel] = [Command.clear()]
        elif line[file_field]:
            values[file_field_norel] = [Command.set(tag_ids)]
        return None

    def _process_other_fields(
        self,
        label_ref,
        model,
        res_object,
        translated_values,
        line,
        file_field,
        file_field_norel,
        fields_odoo,
        i,
        model_data,
        values,
    ):
        """
        Process other fields (char, text, date, ...) from the input line and update the values dictionary.

        :param label_ref: The label reference.
        :param model: The model name.
        :param res_object: The resource object.
        :param translated_values: The translated values dictionary.
        :param line: The line dictionary.
        :param file_field: The file field name.
        :param file_field_norel: The file field name without relation.
        :param fields_odoo: The Odoo fields dictionary.
        :param i: The line number.
        :param model_data: The model data dictionary.
        :param values: The values dictionary.

        :return: The updated label reference and the error message.
        """
        if fields_odoo[file_field_norel]['translate'] and line[file_field] != '':
            lang = self.lang_id.code or 'en_US'
            if lang != 'en_US':
                vals_trans = translated_values.setdefault(lang, {})
                vals_trans[file_field_norel] = '' if line[file_field] == "#empty" else line[file_field]
        if fields_odoo[file_field_norel]['lang']:
            if line[file_field] != '':
                lang = fields_odoo[file_field_norel]['lang']
                vals_trans = translated_values.setdefault(lang, {})
                vals_trans[file_field_norel[len(lang) + 2 :]] = '' if line[file_field] == "#empty" else line[file_field]
        elif line[file_field] == "#empty":
            values[file_field_norel] = ''
        elif line[file_field] != '':
            value = line[file_field]
            if file_field == model_data['reference_field']:
                if model == 'product.template':
                    # On ajoute (ou retire) à la référence d'un article le préfixe défini dans la marque
                    # associée. Cette opération doit être réalisée après la détection de la marque mais
                    # avant la détection du produit associé (la combinaison préfixe+référence est la clef
                    # de recherche)
                    if brand_id := values.get('brand_id'):
                        brand = self.env['of.product.brand'].browse(brand_id)
                    else:
                        brand = res_object.brand_id

                    if brand:
                        prefix = f'{brand.code}_'
                        if brand.use_prefix:
                            # Le préfixe n'est ajouté que s'il n'est pas déjà appliqué
                            # (e.g. avec un export/import)
                            if not value.startswith(prefix):
                                value = prefix + value
                        elif value.startswith(prefix):
                            value = value[len(prefix) :]

                    # la référence de l'article est transférée dans les informations fournisseur
                    values['of_seller_product_code'] = value
                elif self.prefix:
                    value = self.prefix + value

                if value:
                    label_ref = f"ref. {value}"
            if fields_odoo[file_field_norel]['type'] in ['date', 'datetime']:
                try:
                    function = (
                        fields_odoo[file_field_norel]['type'] == 'date'
                        and fields.Date.from_string
                        or fields.Datetime.form_string
                    )
                    function(value)
                except ValueError:  # Value is not a date
                    message = _(
                        "line %(i)s : field %(field)s (%(file_field)s) value \"%(value)s\" has not the good format. "
                        "%(model)s not imported.",
                        i=i,
                        field=fields_odoo[file_field_norel]['description'],
                        file_field=file_field,
                        value=value,
                        model=model_data['object_name'].capitalize(),
                    )
                    return label_ref, message

            values[file_field_norel] = value
        return label_ref, None
