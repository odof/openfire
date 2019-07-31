# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class OfAnalyseChantierWizard(models.TransientModel):
    _name = "of.analyse.chantier.wizard"

    def button_validate(self):
        objs = self.env[self._context.get('origin_model')].browse(self._context.get('active_ids'))
        if len(objs.mapped('partner_id')) > 1:
            raise UserError(u"L'analyse de chantier ne peut être faite sur des documents d'un seul partenaire.")
        elif objs:
            dic = {
                'name' : u"Analyse %s %s" % (objs.mapped('partner_id').name, ", ".join(objs.mapped('display_name'))),
                'order_ids' : objs._name == 'sale.order' and [(4, obj.id) for obj in objs],
                'invoice_ids' : objs._name == 'account.invoice' and [(4, obj.id) for obj in objs],
                }
            analyse = self.env['of.analyse.chantier'].create(dic)
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'of.analyse.chantier',
                'view_type': 'form',
                'view_mode': 'form',
                'res_id': analyse.id,
                'target': 'current',
                'context': self._context
                }
