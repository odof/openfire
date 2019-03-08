# -*- coding: utf-8 -*-

from odoo import models, fields, api

class OfParcInstalle(models.Model):
    _inherit = "of.parc.installe"

    secteur_id = fields.Many2one('of.secteur', string="Secteur")

class OfSecteur(models.Model):
    _name = "of.secteur"

    name = fields.Char(string='Nom', required=True)
    shortcut = fields.Char(string=u'Nom abrégé')
    parc_installe_ids = fields.One2many('of.parc.installe', 'secteur_id', string=u"Parc installé")

    @api.multi
    def name_get(self):
#         val = super(OfSecteur, self).name_get()
        records = []
        for secteur in self:
            records.append((secteur.id, secteur.name + " - " + secteur.shortcut if secteur.shortcut else secteur.name))
        return records

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        if not args:
            args = ['|', ('name', 'ilike', name), ('shortcut', 'ilike', name)]
        access_rights_uid = name_get_uid or self._uid
        ids = self._search(args, limit=limit, access_rights_uid=access_rights_uid)
        recs = self.browse(ids)
        return recs.sudo(access_rights_uid).name_get()
#         return val