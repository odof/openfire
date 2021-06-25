# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AssignManualQuants(models.TransientModel):
    _inherit = 'assign.manual.quants'

    @api.model
    def default_get(self, fields):
        res = super(AssignManualQuants, self).default_get(fields)
        move = self.env['stock.move'].browse(self.env.context['active_id'])
        available_quants = self.env['stock.quant'].search([
            ('location_id', 'child_of', move.location_id.id),
            ('product_id', '=', move.product_id.id),
            ('qty', '>', 0)
        ])
        quants_lines = [{
            'quant': x.id,
            'lot_id': x.lot_id.id,
            'in_date': x.in_date,
            'package_id': x.package_id.id,
            'selected': x in move.reserved_quant_ids,
            'qty': x.qty if x in move.reserved_quant_ids else 0,
            'location_id': x.location_id.id,
            'reservation_id': x.reservation_id.id,
            'reservation_partner_id': x.reservation_id.partner_id.id,
        } for x in available_quants]
        res.update({'quants_lines': quants_lines})
        res = self._convert_to_write(self._convert_to_cache(res))
        return res


class AssignManualQuantsLines(models.TransientModel):
    _inherit = 'assign.manual.quants.lines'

    reservation_id = fields.Many2one(
        comodel_name='stock.move', string=u"Réservé par", related='quant.reservation_id', readonly=True)
    reservation_partner_id = fields.Many2one(
        comodel_name='res.partner', string=u"Partenaire", related='quant.reservation_id.partner_id', readonly=True)
