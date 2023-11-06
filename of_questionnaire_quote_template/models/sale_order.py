# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
from datetime import timedelta


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        active_option = self.env['ir.values'].get_default('sale.config.settings', 'of_active_option')
        if (active_option and self.of_template_id.of_intervention_template_id and
                self.of_template_id.of_intervention_template_id.tache_id):
            today_str = fields.Date.today()
            today_da = fields.Date.from_string(today_str)
            deux_semaines_da = today_da + timedelta(days=14)
            deux_semaines_str = fields.Date.to_string(deux_semaines_da)
            if self.state == 'sale':
                new_service = self.env['of.service'].create({
                    'partner_id': self.partner_id.id,
                    'company_id': self.company_id.id,
                    'address_id': self.partner_shipping_id and self.partner_shipping_id.id or self.partner_id.id,
                    'recurrence': False,
                    'date_next': today_str,
                    'date_fin': deux_semaines_str,
                    'origin': u"[Commande] " + self.name,
                    'order_id': self.id,
                    'hide_bouton_planif': True,
                    'type_id': self.of_template_id.of_intervention_template_id.type_id.id or
                               self.env.ref('of_service.of_service_type_installation').id,
                    'template_id': self.of_template_id.of_intervention_template_id.id,
                    'tache_id': self.of_template_id.of_intervention_template_id.tache_id.id,
                    'duree': self.of_template_id.of_intervention_template_id.tache_id.duree,
                    'parc_installe_id': self.of_parc_installe_ids and self.of_parc_installe_ids[0].id or False,
                })
                new_service.onchange_template_id()
        return res
