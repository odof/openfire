# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class OFCRMProjetLine(models.Model):
    _name = 'of.crm.projet.line'
    _order = 'sequence'

    name = fields.Char(string=u"Libellé", required=True, translate=True)
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
    val_bool = fields.Boolean(string="Valeur", default=False)
    val_char = fields.Char(string="Valeur")
    val_text = fields.Text(string="Valeur")
    val_date = fields.Date(string="Valeur", default=fields.Date.today)
    val_select_id = fields.Many2one(
        'of.crm.projet.attr.select', string="Valeur", ondelete="set null")  # , domain="[('attr_id','=',attr_id)]")
    # val_select_ids = fields.Many2many(
    #     'of.crm.projet.attr.select', 'crm_projet_multiple_rel', 'line_id', 'val_id', string="Valeurs")
    sequence = fields.Integer(string=u'Séquence', default=10)
    type_var_name = fields.Char(string="nom de la variable de valeur", compute="_compute_type_var_name")

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
