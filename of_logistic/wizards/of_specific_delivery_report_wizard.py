# -*- coding: utf-8 -*-

from odoo import api, fields, models


class OFSpecificDeliveryReportWizard(models.TransientModel):
    _inherit = 'of.specific.delivery.report.wizard'

    total_weight = fields.Float(string="Total weight", compute='_compute_total_weight', digits=(16, 2))
    nbr_pallets = fields.Integer(string="Nbr. of pallets", compute='_compute_nbr_pallets')
    packages = fields.Integer(string="Packages", compute='_compute_packages')
    of_carrier_id = fields.Many2one(comodel_name='res.partner', string="Carrier", compute='_compute_carrier_id')

    @api.depends('line_ids', 'line_ids.selected')
    def _compute_total_weight(self):
        for wizard in self:
            moves = wizard.line_ids.filtered('selected').mapped('move_id')
            total_weight = 0.0
            for line in moves:
                if line.product_id:
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
                if line.product_id:
                    product = line.product_id
                    product_uom = product.uom_id
                    move_uom = line.product_uom
                    # Since the values are for the UOM of the product, convert the qty to the one of the product
                    # _compute_price also works for quantities since it only applies the factors
                    qty = move_uom._compute_price(line.product_uom_qty, product_uom)
                    nbr_pallets += qty * product.of_nbr_pallets
            wizard.nbr_pallets = nbr_pallets

    @api.depends('line_ids', 'line_ids.selected')
    def _compute_packages(self):
        for wizard in self:
            moves = wizard.line_ids.filtered('selected').mapped('move_id')
            total_packages = 0.0
            for line in moves:
                if line.product_id:
                    product = line.product_id
                    product_uom = product.uom_id
                    move_uom = line.product_uom
                    # Since the values are for the UOM of the product, convert the qty to the one of the product
                    # _compute_price also works for quantities since it only applies the factors
                    qty = move_uom._compute_price(line.product_uom_qty, product_uom)
                    total_packages += qty * product.of_packages
            wizard.packages = total_packages

    @api.depends('picking_id.of_rate_ids.selected')
    def _compute_carrier_id(self):
        for wizard in self:
            wizard.of_carrier_id = wizard.picking_id.of_rate_ids.filtered('selected').partner_id


class OFDeliveryDivisionWizardLine(models.TransientModel):
    _inherit = 'of.specific.delivery.report.wizard.line'

    product_weight = fields.Float(string="Weight", compute='_compute_of_product_weight')

    @api.depends('product_id', 'move_id.product_uom', 'move_id.product_uom_qty')
    def _compute_of_product_weight(self):
        for line in self:
            if line.product_id:
                product = line.move_id.product_id
                product_uom = product.uom_id
                move_uom = line.move_id.product_uom
                # Since the values are for the UOM of the product, convert the qty to the one of the product
                # _compute_price also works for quantities since it only applies the factors
                qty = move_uom._compute_price(line.move_id.product_uom_qty, product_uom)
                line.product_weight = qty * product.weight
