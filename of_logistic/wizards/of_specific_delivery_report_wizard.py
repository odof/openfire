# -*- coding: utf-8 -*-

from odoo import api, fields, models


class OFSpecificDeliveryReportWizard(models.TransientModel):
    _inherit = 'of.specific.delivery.report.wizard'

    total_weight = fields.Float(string="Total weight", compute='_compute_total_weight', digits=(16, 2))
    nbr_pallets = fields.Integer(string="Nbr. of pallets", compute='_compute_nbr_pallets')

    @api.depends('line_ids', 'line_ids.selected')
    def _compute_total_weight(self):
        for wizard in self:
            moves = wizard.line_ids.filtered('selected').mapped('move_id')
            total_weight = 0.0
            for line in moves:
                product = line.product_id
                product_uom = product.uom_id
                move_uom = line.product_uom
                # Since the values are for the UOM of the product, convert the qty to the one of the product
                # _compute_price also works for quantities since it only applies the factors
                qty = move_uom._compute_price(line.product_uom_qty, product_uom)
                total_weight += qty * product.weight
            wizard.total_weight = total_weight

    @api.depends('line_ids', 'line_ids.selected')
    def _compute_nbr_pallets(self):
        for wizard in self:
            moves = wizard.line_ids.filtered('selected').mapped('move_id')
            nbr_pallets = 0.0
            for line in moves:
                product = line.product_id
                product_uom = product.uom_id
                move_uom = line.product_uom
                # Since the values are for the UOM of the product, convert the qty to the one of the product
                # _compute_price also works for quantities since it only applies the factors
                qty = move_uom._compute_price(line.product_uom_qty, product_uom)
                nbr_pallets += qty * product.of_nbr_pallets
            wizard.total_weight = nbr_pallets
