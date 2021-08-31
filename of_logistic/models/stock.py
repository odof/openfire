# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockPickingLogisticRate(models.Model):
    _name = 'of.stock.picking.logistic.rate'
    _order = 'constraint DESC, rate ASC'

    @api.model
    def _get_constraint_selection(self):
        """
        By doing this, we make sure that the constraint field always has the same options as the field
        type from of.logistic.constraint
        """
        return self.env['of.logistic.constraint']._fields['type'].selection

    picking_id = fields.Many2one(comodel_name='stock.picking', string="Picking")
    partner_id = fields.Many2one(comodel_name='res.partner', string="Carrier")
    min_weight = fields.Float(string="Min. weight")
    max_weight = fields.Float(string="Max. weight")
    rate = fields.Float(string="Computed rate")
    constraint = fields.Selection(selection=lambda s : s._get_constraint_selection(), string="Constraint")
    selected = fields.Boolean(string="Selected")


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    of_department_id = fields.Many2one(
        comodel_name='res.country.department', string="Department", compute='_compute_of_department_id')
    of_nbr_pallets = fields.Integer(string="Nbr. of pallets")
    of_total_volume = fields.Float(string="Total volume")
    of_total_weight = fields.Float(string="Total weight")
    of_rate_ids = fields.One2many(
        comodel_name='of.stock.picking.logistic.rate', inverse_name='picking_id', string="Computed rates")

    @api.depends('partner_id')
    def _compute_of_department_id(self):
        for picking in self:
            picking.of_department_id = picking.partner_id.department_id

    @api.multi
    def compute_logistic_informations(self):
        self.ensure_one()
        total_pallets = 0
        total_volume = 0.0
        total_weight = 0.0
        for line in self.move_lines:
            product = line.product_id
            product_uom = product.uom_id
            move_uom = line.product_uom
            # Since the values are for the UOM of the product, convert the qty to the one of the product
            # _compute_price also works for quantities since it only applies the factors
            qty = move_uom._compute_price(line.product_uom_qty, product_uom)
            total_pallets += qty * product.of_nbr_pallets
            total_volume += qty * product.volume
            total_weight += qty * product.weight
        self.write({
            'of_nbr_pallets' : total_pallets,
            'of_total_volume': total_volume,
            'of_total_weight': total_weight,
            })

    @api.multi
    def compute_logistic_rates(self):
        self.ensure_one()
        if not self.of_department_id:
            raise UserError(_("Missing department to compute the logistic rates."))
        rate_obj = self.env['of.logistic.rate']
        constraint_obj = self.env['of.logistic.constraint']
        # Find rates within perimeter
        rates = rate_obj.search([('date_start', '<=', self.min_date),
                                 ('date_end', '>', self.min_date),
                                 ('department_id', '=', self.of_department_id.id),
                                 ('min_weight', '<=', self.of_total_weight),
                                 ('max_weight', '>', self.of_total_weight)])
        if not rates:  # No rates found, warn user
            return self.env['of.popup.wizard'].popup_return(message=_("No corresponding rates."))

        # Find applicable constraints for the rates
        partners = rates.mapped('partner_id')
        constraints = constraint_obj.search([('partner_id', 'in', partners.ids)])

        new_rates = [(5,)]
        for rate in rates:
            # Only look at the constraints of the carrier
            rate_constraints = constraints.filtered(lambda c: c.partner_id.id == rate.partner_id.id)
            broken_constraint = rate_constraints.verify_constraints(
                weight=self.of_total_weight, pallets=self.of_nbr_pallets
            )
            if broken_constraint:
                new_rates.append(
                    (0, 0, {
                        'partner_id': rate.partner_id.id,
                        'min_weight': rate.min_weight,
                        'max_weight': rate.max_weight,
                        'rate': 0.0,
                        'constraint': broken_constraint.type,
                        }
                    )
                )
            else:
                new_rates.append(
                    (0, 0, {
                        'partner_id': rate.partner_id.id,
                        'min_weight': rate.min_weight,
                        'max_weight': rate.max_weight,
                        'rate': rate.compute_rate_by_weight(self.of_total_weight),
                        }
                    )
                )
        self.write({'of_rate_ids': new_rates})
        return True

    @api.multi
    def button_compute_logistics(self):
        self.compute_logistic_informations()
        # compute_logistic_rates may raise errors, we still want to update the logistic informations.
        self.env.cr.commit()
        return self.compute_logistic_rates()


class StockMove(models.Model):
    _inherit = 'stock.move'

    of_product_weight = fields.Float(string="Weight", compute='_compute_of_product_weight')

    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_of_product_weight(self):
        for move in self:
            if move.product_id:
                product = move.product_id
                product_uom = product.uom_id
                move_uom = move.product_uom
                # Since the values are for the UOM of the product, convert the qty to the one of the product
                # _compute_price also works for quantities since it only applies the factors
                qty = move_uom._compute_price(move.product_uom_qty, product_uom)
                move.of_product_weight = qty * product.weight


class StockPackOperation(models.Model):
    _inherit = 'stock.pack.operation'

    of_product_weight = fields.Float(string="Weight", compute='_compute_of_product_weight')

    @api.depends('product_id', 'product_qty', 'product_uom_id')
    def _compute_of_product_weight(self):
        for operation in self:
            if operation.product_id:
                product = operation.product_id
                product_uom = product.uom_id
                operation_uom = operation.product_uom_id
                # Since the values are for the UOM of the product, convert the qty to the one of the product
                # _compute_price also works for quantities since it only applies the factors
                qty = operation_uom._compute_price(operation.product_qty, product_uom)
                operation.of_product_weight = qty * product.weight
