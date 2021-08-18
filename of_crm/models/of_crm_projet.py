# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval


class OFCRMProjetLine(models.Model):
    _name = 'of.crm.projet.line'
    _order = 'sequence'

    @api.model_cr_context
    def _auto_init(self):
        # auto_init temporaire pour l'ajout des champs 'is_answered' et affiliés
        cr = self._cr
        cr.execute("SELECT 1 FROM information_schema.columns "
                   "WHERE table_name = 'of_crm_projet_line' AND column_name = 'is_answered'")
        is_answered_exists = bool(cr.fetchall())
        res = super(OFCRMProjetLine, self)._auto_init()

        if not is_answered_exists:
            # Initialisation des champs
            cr.execute("UPDATE of_crm_projet_line "
                       "SET is_answered = 't',  answer_date = write_date, "
                       "answer_user_id = write_uid, answer_init_user_id = create_uid "
                       "WHERE type = 'bool' "
                       "OR type = 'char' AND val_char IS NOT NULL AND val_char != '' "
                       "OR type = 'text' AND val_text IS NOT NULL AND val_text != '' "
                       "OR type = 'selection' AND val_select_id IS NOT NULL "
                       "OR type = 'date' AND val_date IS NOT NULL")
        return res

    name = fields.Char(string=u"Question", required=True, translate=True)
    lead_id = fields.Many2one('crm.lead', string=u"Opportunité", required=True, ondelete="cascade")
    attr_id = fields.Many2one('of.crm.projet.attr', string="Attribut", required=True, ondelete="restrict")
    type = fields.Selection([
        ('bool', u'Booléen (Oui/Non)'),
        ('char', u'Texte Court'),
        ('text', u'Texte Long'),
        ('selection', u'Choix Unique'),
        # ('multiple',u'Choix Multiple'), # plus tard
        ('date', u'Date'),
        ], string=u'Type', required=True, default='char')
    # xml will not display val_bool and val_select_id if type set to 'char'
    val_bool = fields.Boolean(string=u"Réponse")
    val_char = fields.Char(string=u"Réponse")
    val_text = fields.Text(string=u"Réponse")
    val_date = fields.Date(string=u"Réponse")
    val_select_id = fields.Many2one(
        'of.crm.projet.attr.select', string=u"Réponse", ondelete="set null")  # , domain="[('attr_id','=',attr_id)]")
    # val_select_ids = fields.Many2many(
    #     'of.crm.projet.attr.select', 'crm_projet_multiple_rel', 'line_id', 'val_id', string="Valeurs")
    sequence = fields.Integer(string=u'Séquence', default=10)
    type_var_name = fields.Char(string="nom de la variable de réponse", compute="_compute_type_var_name")

    is_answered = fields.Boolean(string=u"A été répondue")
    answer_date = fields.Date(string=u"Date de la réponse")
    answer_user_id = fields.Many2one(string=u"Auteur de la réponse", comodel_name='res.users')
    answer_last = fields.Text(string=u"Réponse précédente")
    answer_last_date = fields.Date(string=u"Date réponse précédente")
    answer_init_user_id = fields.Many2one(string=u"Auteur réponse initiale", comodel_name='res.users', readonly=True)

    @api.multi
    @api.depends('type')
    def _compute_type_var_name(self):
        for line in self:
            if line.type == 'bool':
                line.type_var_name = 'val_bool'
            elif line.type == 'char':
                line.type_var_name = 'val_char'
            elif line.type == 'text':
                line.type_var_name = 'val_text'
            elif line.type == 'date':
                line.type_var_name = 'val_date'
            else:
                line.type_var_name = 'val_select_id'

    @api.onchange('attr_id')
    def _onchange_attr_id(self):
        if self.attr_id:
            vals = {
                'type': self.attr_id.type,
                'name': self.attr_id.name,
                'sequence': self.attr_id.sequence,
                }
            self.update(vals)

    @api.multi
    def action_edit_answer(self):
        u"""Ouvrir la ligne de projet et signaler (par le context) de mettre à jour les champs de réponse précédente"""
        action = self.env.ref('of_crm.action_of_crm_projet_line_form').read()[0]
        if len(self._ids) == 1:
            context = safe_eval(action['context'])
            context['create'] = False
            context['update_last_answer'] = True
            action['context'] = str(context)
            action['target'] = 'new'
            action['res_id'] = self.id
        return action

    @api.model
    def create(self, vals):
        type = vals.get('type')
        # on a une réponse -> on initialise la date et l'utilisateur
        if type and (type == 'char' and vals.get('val_char')
                     or type == 'bool'
                     or type == 'text' and vals.get('val_text')
                     or type == 'date' and vals.get('val_date')
                     or type == 'selection' and vals.get('val_select_id')):
            vals['answer_date'] = fields.Date.today()
            vals['answer_user_id'] = self.env.user.id
            vals['answer_init_user_id'] = self.env.user.id
            vals['is_answered'] = True
        return super(OFCRMProjetLine, self).create(vals)

    @api.multi
    def write(self, vals):
        if len(self) == 1:
            set_answer = {'val_bool', 'val_char', 'val_text', 'val_date', 'val_select_id'}
            set_vals = set(vals)
            if set_answer & set_vals:
                if self.is_answered and self._context.get('update_last_answer'):
                    # modification de réponse : on stocke les informations de la réponse précédente
                    vals['answer_last'] = self.get_name_and_val()[1]
                    vals['answer_last_date'] = self.answer_date
                vals['is_answered'] = True
                vals['answer_date'] = fields.Date.today()
                vals['answer_user_id'] = self.env.user.id
        return super(OFCRMProjetLine, self).write(vals)

    @api.multi
    def name_get(self):
        return [(record.id, "%s:%s" % (record.name, getattr(record, record.type_var_name)))
                for record in self]

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        """
        Système de recherche avancé permettant d'utiliser une syntaxe de type 'nom_attribut:valeur'
        Si name ne contient pas de ':', recherche sur valeurs uniquement
        """
        name = name.split(':')
        if len(name) == 1:
            value = name[0]
            name = False
        else:
            value = ':'.join(name[1:])
            name = name[0]

        args = list(args or [])
        if name:
            args.append(('name', 'ilike', name))

        name_args = []
        nb_name_args = 0
        if value in '01' and operator in ('=', '!='):
            # Cas particulier du champ booleen
            name_args.append(('val_bool', operator, value == '1'))
            nb_name_args = 1
        # op = operator in NEGATIVE_TERM_OPERATORS and '&' or '|'
        if value:
            for field_type, field_name in (('char', 'val_char'), ('text', 'val_text'), 
                                           ('date', 'val_date'), ('selection', 'val_select_id')):
                name_args += ['&', ('type', '=', field_type), (field_name, operator, value)]
            nb_name_args += 4
        if name_args:
            args = args + ['|'] * (nb_name_args-1) + name_args
        return super(OFCRMProjetLine, self)._name_search('', args, 'ilike', limit, name_get_uid)

    def get_name_and_val(self):
        self.ensure_one()
        if self.type == 'bool':
            # value = "Oui" if self.val_bool  else "Non"
            value = ("Non", "Oui")[self.val_bool]
        elif self.type == 'char':
            value = self.val_char
        elif self.type == 'text':
            value = self.val_text
        elif self.type == 'date':
            value = self.val_date
        else:
            value = self.val_select_id.name
        return self.name, value


class OFCRMProjetModele(models.Model):
    _name = 'of.crm.projet.modele'

    name = fields.Char(string=u"Libellé", required=True, translate=True)
    attr_ids = fields.Many2many(
        'of.crm.projet.attr', 'crm_projet_modele_attr_rel', 'modele_id', 'attr_id', string='Attributs',
        help=u"Liste des attributs de ce modèle. Ils seront copiés dans la fiche projet si ce modèle est sélectionné.")
    active = fields.Boolean(string="Actif", default=True)


class OFCRMProjetAttr(models.Model):
    _name = 'of.crm.projet.attr'
    _order = 'sequence'

    name = fields.Char(string=u"Libellé", required=True, translate=True)
    description = fields.Text(string="Description", translate=True)
    type = fields.Selection([
        ('bool', u'Booléen (Oui/Non)'),
        ('char', u'Texte Court'),
        ('text', u'Texte Long'),
        ('selection', u'Choix Unique'),
        # ('multiple',u'Choix Multiple'), # plus tard
        ('date', u'Date'),
        ], string=u'Type', required=True, default='char')
    selection_ids = fields.One2many('of.crm.projet.attr.select', 'attr_id', string="Valeurs")
    modele_ids = fields.Many2many(
        'of.crm.projet.modele', 'crm_projet_modele_attr_rel', 'attr_id', 'modele_id', string='Projets')
    active = fields.Boolean(string="Actif", default=True)
    sequence = fields.Integer(string=u'Séquence', default=10)

    val_bool_default = fields.Boolean(string=u"Valeur par Défaut", default=False)
    val_char_default = fields.Char(string=u"Valeur par Défaut")
    val_text_default = fields.Text(string=u"Valeur par Défaut")
    # val_date_default = fields.Date(string="Valeur par Défaut", default=fields.Date.today)
    val_select_id_default = fields.Many2one(
        'of.crm.projet.attr.select', string=u"Valeur par Défaut", domain="[('attr_id','=',id)]", ondelete="set null")

    @api.multi
    def write(self, vals):
        super(OFCRMProjetAttr, self).write(vals)
        if 'active' in vals:
            select_obj = self.env['of.crm.projet.attr.select'].with_context(active_test=False)
            select_values = select_obj.search([('attr_id', 'in', self._ids)])
            select_values.write({'active': vals['active']})
        return True


class OFCRMProjetAttrSelect(models.Model):
    _name = 'of.crm.projet.attr.select'
    _order = 'attr_id,sequence'

    name = fields.Char(string=u"Libellé", required=True, translate=True)
    description = fields.Text(string="Description", translate=True)
    attr_id = fields.Many2one(
        'of.crm.projet.attr', string="Attribut", required=True, domain="[('type','in',('selection','multiple'))]",
        ondelete="cascade")
    sequence = fields.Integer(string=u'Séquence', default=10)
    active = fields.Boolean(string="Actif", default=True)

    @api.multi
    def write(self, vals):
        if 'active' in vals and len(self._ids) == 1:
            if not self.attr_id.active:
                raise ValidationError(u"L'attribut associé à cette valeur est désactivé")
        return super(OFCRMProjetAttrSelect, self).write(vals)
