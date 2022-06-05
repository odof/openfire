# -*- coding: utf-8 -*-

from odoo import api, models, fields
from datetime import timedelta
from odoo.tools.safe_eval import safe_eval


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # Utilisé pour ajouter bouton Interventions à Devis (see order_id many2one field above)
    of_service_ids = fields.One2many("of.service", "order_id", string=u"DI à programmer", oldname="of_a_programmer_ids")
    of_service_count = fields.Integer(string=u"Nb DI à programmer", compute='_compute_of_service_count')

    # @api.depends

    @api.depends('of_service_ids', 'order_line.of_service_line_id')
    @api.multi
    def _compute_of_service_count(self):
        for sale_order in self:
            services = sale_order.of_service_ids.filtered(lambda s: s.state != 'cancel')
            services |= sale_order.order_line.mapped('of_service_line_id').mapped('service_id')
            sale_order.of_service_count = len(services)

    # Actions

    @api.multi
    def action_view_a_programmer(self):
        action = self.env.ref('of_service.of_sale_order_open_a_programmer').read()[0]

        service_ids = self.mapped('order_line').mapped('of_service_line_id').mapped('service_id').ids
        action['domain'] = ['|', ('order_id', 'in', self.ids), ('id', 'in', service_ids)]
        if len(self._ids) == 1:
            context = safe_eval(action['context'])
            context.update({
                'default_partner_id': self.partner_id.id,
                'default_address_id': self.partner_shipping_id.id or self.partner_id.id,
                'default_order_id': self.id,
            })
            action['context'] = str(context)
        return action

    @api.multi
    def action_prevoir_intervention(self):
        self.ensure_one()
        action = self.env.ref('of_service.action_of_service_prog_form_planning').read()[0]
        today_str = fields.Date.today()
        today_da = fields.Date.from_string(today_str)
        deux_semaines_da = today_da + timedelta(days=14)
        deux_semaines_str = fields.Date.to_string(deux_semaines_da)
        action['name'] = u"Prévoir une intervention"
        action['view_mode'] = "form"
        action['view_ids'] = False
        action['view_id'] = self.env['ir.model.data'].xmlid_to_res_id("of_service.view_of_service_form")
        action['views'] = False
        action['target'] = "new"
        action['context'] = {
            'default_partner_id': self.partner_id.id,
            'default_address_id': self.partner_shipping_id and self.partner_shipping_id.id or self.partner_id.id,
            'default_recurrence': False,
            'default_date_next': today_str,
            'default_date_fin': deux_semaines_str,
            'default_origin': u"[Commande] " + self.name,
            'default_order_id': self.id,
            'hide_bouton_planif': True,
            'default_type_id': self.env.ref('of_service.of_service_type_installation').id,
        }
        return action


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_service_line_id = fields.Many2one(comodel_name='of.service.line', string=u"Ligne de DI")
