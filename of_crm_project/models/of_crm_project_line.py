# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval


class OFCRMProjectLine(models.Model):
    _name = 'of.crm.project.line'
    _order = 'sequence'

    name = fields.Char(string="Question", required=True, translate=True)
    lead_id = fields.Many2one('crm.lead', string="Opportunity", required=True, ondelete="cascade")
    company_id = fields.Many2one(comodel_name='res.company', related='lead_id.company_id', store=True, string="Company")
    attr_id = fields.Many2one('of.crm.project.attr', string="Attribute", required=True, ondelete="restrict")
    type = fields.Selection(
        [
            ('bool', "Booléen (Oui/Non)"),
            ('char', "Texte Court"),
            ('text', "Texte Long"),
            ('selection', "Choix Unique"),
            # ('multiple',"Choix Multiple"), # plus tard
            ('date', "Date"),
        ],
        required=True,
        default='char',
    )
    # xml will not display val_bool and val_select_id if type set to 'char'
    val_bool = fields.Boolean(string="Réponse")
    val_char = fields.Char(string="Réponse")
    val_text = fields.Text(string="Réponse")
    val_date = fields.Date(string="Réponse")
    val_select_id = fields.Many2one(
        'of.crm.project.attr.select', string="Réponse", ondelete="set null"
    )  # , domain="[('attr_id','=',attr_id)]")
    # val_select_ids = fields.Many2many(
    #     'of.crm.project.attr.select', 'crm_project_multiple_rel', 'line_id', 'val_id', string="Valeurs")
    sequence = fields.Integer(default=10)
    type_var_name = fields.Char(string="Nom de la variable de réponse", compute="_compute_type_var_name")

    is_answered = fields.Boolean(string="A eu une réponse")
    is_corrected = fields.Boolean(string="A été corrigé", compute='_compute_is_corrected', store=True)
    answer_date = fields.Date()
    answer_user_id = fields.Many2one(string="Auteur de la réponse", comodel_name='res.users')
    answer_orig = fields.Text(string="Réponse d'origine")
    answer_orig_date = fields.Date(string="Date réponse d'origine")
    answer_orig_user_id = fields.Many2one(string="Auteur réponse d'origine", comodel_name='res.users', readonly=True)

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

    @api.depends('answer_user_id')
    def _compute_is_corrected(self):
        for line in self:
            line.is_corrected = line.answer_user_id and line.answer_user_id != line.answer_orig_user_id

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
        """Ouvrir la ligne de projet et signaler (par le context) de mettre à jour les champs de réponse précédente"""
        action = self.env.ref('of_crm.action_of_crm_project_line_form').read()[0]
        if len(self._ids) == 1:
            context = safe_eval(action['context'])
            context['create'] = False
            # context['update_last_answer'] = True
            action['context'] = str(context)
            action['target'] = 'new'
            action['res_id'] = self.id
        return action

    @api.model
    def create(self, vals):
        line_type = vals.get('type')
        # on a une réponse -> on initialise la date et l'utilisateur
        if line_type and (
            line_type == 'char'
            and vals.get('val_char')
            or line_type == 'bool'
            or line_type == 'text'
            and vals.get('val_text')
            or line_type == 'date'
            and vals.get('val_date')
            or line_type == 'selection'
            and vals.get('val_select_id')
        ):
            field = 'val_' + line_type
            if line_type == 'selection':
                field = 'val_select_id'
            vals['answer_orig'] = self.val_to_text(line_type, vals[field])
            vals['answer_date'] = fields.Date.today()
            vals['answer_orig_date'] = fields.Date.today()
            vals['answer_user_id'] = self.env.user.id
            vals['answer_orig_user_id'] = self.env.user.id
            vals['is_answered'] = True
        res = super(OFCRMProjectLine, self).create(vals)
        if res.answer_orig_date and not res.answer_orig:
            res.answer_orig = res.get_name_and_val()[1]
        return res

    @api.multi
    def write(self, vals):
        if len(self) == 1:
            field = 'val_' + self.type
            if self.type == 'selection':
                field = 'val_select_id'
            if field in vals:
                if not self.is_answered:
                    if not vals[field]:
                        # Erreur de manip' ?
                        return super(OFCRMProjectLine, self).write(vals)
                    # Première réponse à la question : on stocke les informations
                    vals['answer_orig'] = self.val_to_text(self.type, vals[field])
                    vals['answer_orig_date'] = fields.Date.today()
                    vals['answer_orig_user_id'] = self.env.user.id
                    vals['is_answered'] = True
                vals['answer_date'] = fields.Date.today()
                vals['answer_user_id'] = self.env.user.id
        return super(OFCRMProjectLine, self).write(vals)

    @api.multi
    def name_get(self):
        return [(record.id, "%s:%s" % (record.name, getattr(record, record.type_var_name))) for record in self]

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
            for field_type, field_name in (
                ('char', 'val_char'),
                ('text', 'val_text'),
                ('date', 'val_date'),
                ('selection', 'val_select_id'),
            ):
                name_args += ['&', ('type', '=', field_type), (field_name, operator, value)]
            nb_name_args += 4
        if name_args:
            args = args + ['|'] * (nb_name_args - 1) + name_args
        return super(OFCRMProjectLine, self)._name_search('', args, 'ilike', limit, name_get_uid)

    @api.model
    def val_to_text(self, line_type, val):
        if line_type == 'bool':
            res = val and "Oui" or "Non"
        elif line_type == 'char':
            res = val
        elif line_type == 'text':
            res = val
        elif line_type == 'date':
            res = val
        else:
            if isinstance(val, int):
                val = self.env['of.crm.project.attr.select'].browse(val)
            res = val.name
        return res

    def get_name_and_val(self):
        self.ensure_one()
        field = 'val_' + self.type
        if self.type == 'selection':
            field = 'val_select_id'
        value = self.val_to_text(self.type, self[field])
        return self.name, value
