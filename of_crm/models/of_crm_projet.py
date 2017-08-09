# -*- coding: utf-8 -*-

from odoo import models, fields, api

class OFCRMProjetLine(models.Model):
    _name = 'of.crm.projet.line'
    _order = 'sequence'

    name = fields.Char(string=u"Libellé", required=True, translate=True)
    lead_id = fields.Many2one('crm.lead', string="Opportunité", required=True)
    attr_id = fields.Many2one('of.crm.projet.attr', string="Attribut", required=True)
    type = fields.Selection([
        ('bool', u'Booléen'),
        ('char', u'Texte court'),
        ('selection', u'Choix Unique'),
        #('multiple',u'Choix Multiple') # plus tard
        ('date',u'Date'),
        ], string=u'Type', required=True, default='char')
    # xml will not display val_bool and val_select_id if type set to 'char'
    val_bool = fields.Boolean(string="Valeur", default=False)
    val_char = fields.Char(string="Valeur")
    val_date = fields.Date(string="Valeur", default=fields.Date.today)
    val_select_id = fields.Many2one('of.crm.projet.attr.select', string="Valeur")#, domain="[('attr_id','=',attr_id)]")
    #val_select_ids = fields.Many2many('of.crm.projet.attr.select', string="Valeurs")
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
        #('multiple',u'Choix Multiple') # plus tard
        ('date',u'Date'),
        ], string=u'Type', required=True, default='char')
    selection_ids = fields.One2many('of.crm.projet.attr.select', 'attr_id', string="Valeurs")
    modele_ids = fields.Many2many('of.crm.projet.modele', 'crm_projet_modele_attr_rel', 'attr_id', 'modele_id', string='Modèles')
    active = fields.Boolean(string="Actif", default=True)

    #def get_select_default_val(self):
    #    self.ensure_one()
    #    if len(self.selection_ids):
            

class OFCRMProjetAttrSelect(models.Model):
    _name = 'of.crm.projet.attr.select'
    _order = 'attr_id,sequence'

    name = fields.Char(string=u"Libellé", required=True, translate=True)
    description = fields.Text(string="Description", translate=True)
    attr_id = fields.Many2one('of.crm.projet.attr', string="Attribut", required=True, domain="[('type','in',('selection','multiple'))]")
    sequence = fields.Integer(string=u'Séquence', default=10)
    active = fields.Boolean(string="Actif", default=True)
