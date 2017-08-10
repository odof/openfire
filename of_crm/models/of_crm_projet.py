# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class OFCRMProjetLine(models.Model):
    _name = 'of.crm.projet.line'
    _order = 'sequence'

    name = fields.Char(string=u"Libellé", required=True, translate=True)
    lead_id = fields.Many2one('crm.lead', string="Opportunité", required=True, ondelete="cascade")
    attr_id = fields.Many2one('of.crm.projet.attr', string="Attribut", required=True, ondelete="restrict")
    type = fields.Selection([
        ('bool', u'Booléen'),
        ('char', u'Texte court'),
        ('selection', u'Choix Unique'),
        #('multiple',u'Choix Multiple'), # plus tard
        ('date',u'Date'),
        ], string=u'Type', required=True, default='char')
    # xml will not display val_bool and val_select_id if type set to 'char'
    val_bool = fields.Boolean(string="Valeur", default=False)
    val_char = fields.Char(string="Valeur")
    val_date = fields.Date(string="Valeur", default=fields.Date.today)
    val_select_id = fields.Many2one('of.crm.projet.attr.select', string="Valeur", ondelete="set null")#, domain="[('attr_id','=',attr_id)]")
    #val_select_ids = fields.Many2many('of.crm.projet.attr.select', 'crm_projet_multiple_rel', 'line_id', 'val_id', string="Valeurs")
    sequence = fields.Integer(string=u'Séquence', default=10)

    @api.onchange('attr_id')
    def _onchange_attr_id(self):
        if self.attr_id:
            vals = {
                'type': self.attr_id.type,
                'name': self.attr_id.name,
                }
            self.update(vals)

class OFCRMProjetModele(models.Model):
    _name = 'of.crm.projet.modele'

    name = fields.Char(string=u"Libellé", required=True, translate=True)
    attr_ids = fields.Many2many('of.crm.projet.attr', 'crm_projet_modele_attr_rel', 'modele_id', 'attr_id', string='Attributs', help=u"""
Liste des attributs de ce modèle. Ils seront copiés dans la fiche projet si ce modèle est sélectionné.
    """)
    active = fields.Boolean(string="Actif", default=True)

class OFCRMProjetAttr(models.Model):
    _name = 'of.crm.projet.attr'

    name = fields.Char(string=u"Libellé", required=True, translate=True)
    description = fields.Text(string="Description", translate=True)
    type = fields.Selection([
        ('bool', u'Booléen'),
        ('char', u'Texte Court'),
        ('selection', u'Choix Unique'),
        #('multiple',u'Choix Multiple'), # plus tard
        ('date',u'Date'),
        ], string=u'Type', required=True, default='char')
    selection_ids = fields.One2many('of.crm.projet.attr.select', 'attr_id', string="Valeurs")
    modele_ids = fields.Many2many('of.crm.projet.modele', 'crm_projet_modele_attr_rel', 'attr_id', 'modele_id', string='Modèles')
    active = fields.Boolean(string="Actif", default=True)

    """@api.onchange('active')
    def _onchange_active(self):
        select_obj = self.env['of.crm.projet.attr.select'].with_context(active_test=False)
        values = select_obj.search([('attr_id','in',self._ids)])
        print self._ids
        print values"""

    #def get_select_default_val(self):
    #    self.ensure_one()
    #    if len(self.selection_ids):

    @api.multi
    def write(self,vals):
        super(OFCRMProjetAttr,self).write(vals)
        if 'active' in vals:
            select_obj = self.env['of.crm.projet.attr.select'].with_context(active_test=False)
            select_values = select_obj.search([('attr_id','in',self._ids)])
            select_values.write({'active': vals['active']})
        return True

class OFCRMProjetAttrSelect(models.Model):
    _name = 'of.crm.projet.attr.select'
    _order = 'attr_id,sequence'

    name = fields.Char(string=u"Libellé", required=True, translate=True)
    description = fields.Text(string="Description", translate=True)
    attr_id = fields.Many2one('of.crm.projet.attr', string="Attribut", required=True, domain="[('type','in',('selection','multiple'))]", ondelete="cascade")
    sequence = fields.Integer(string=u'Séquence', default=10)
    active = fields.Boolean(string="Actif", default=True)

    @api.multi
    def write(self,vals):
        if 'active' in vals and len(self._ids) == 1:
            if not self.attr_id.active:
                raise ValidationError(u"l'Attribut associé à cette valeur est désactivé")
        return super(OFCRMProjetAttrSelect,self).write(vals)
