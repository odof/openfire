# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools.float_utils import float_compare
from odoo.exceptions import UserError, ValidationError


class OfLogisticRate(models.Model):
    _name = 'of.logistic.rate'

    def _get_company_id_default(self):
        return self.env.user.company_id.id

    name = fields.Char(string="Name", compute='_compute_name')
    date_start = fields.Date(string="Date start", required=True)
    date_end = fields.Date(string="Date end", required=True)
    partner_id = fields.Many2one(comodel_name='res.partner', string="Carrier", required=True)
    department_id = fields.Many2one(comodel_name='res.country.department', name="Department")
    min_weight = fields.Float(string="Min. value (kg)", required=True, digits=(16, 2))
    max_weight = fields.Float(string="Max. value (kg)", required=True, digits=(16, 2))
    type = fields.Selection([
        ('flat_rate', 'Flat rate'),
        ('10kg', 'Rate/10kg'),
        ('100kg', 'Rate/100kg'),
        ], required=True)
    company_id = fields.Many2one(
        comodel_name='res.company', string="Company", default=lambda r : r._get_company_id_default(), required=True)
    company_currency_id = fields.Many2one('res.currency', compute='_compute_company_currency_id')
    rate = fields.Monetary(string="Rate", currency_field='company_currency_id', required=True)
    # Rounding should always be 'round_value'
    # rounding = fields.Selection([
    #     ('round_1', 'Round/kg'),
    #     ('round_10', 'Round/10kg'),
    #     ('round_100', 'Round/100kg'),
    #     ], string="Rounding", required=True)

    @api.constrains('date_start', 'date_end')
    def constraint_dates(self):
        if self.date_start and self.date_end and self.date_end <= self.date_start:
            raise ValidationError("The end date must be later than the start date.")

    @api.constrains('min_weight', 'max_weight')
    def constraint_weights(self):
        if self.min_weight and self.max_weight and self.max_weight <= self.min_weight:
            raise ValidationError("The maximum weight must be superior than the minimum weight/")

    @api.depends()
    def _compute_name(self):
        type_selection = dict(self._fields['type'].selection)
        for rate in self:
            rate.name = "%s - %s" % (rate.partner_id.name, type_selection.get(rate.type))

    @api.depends('company_id')
    def _compute_company_currency_id(self):
        for rate in self:
            rate.company_currency_id = rate.company_id.currency_id

    # @api.multi
    # def get_rounding(self):
    #     self.ensure_one()
    #     return int(self.rounding[6:])

    @api.onchange('date_start', 'date_end')
    def onchange_dates(self):
        if self.date_start and self.date_end and self.date_end <= self.date_start:
            raise UserError("The end date must be later than the start date.")

    @api.onchange('min_weight', 'max_weight')
    def onchange_weights(self):
        if self.min_weight and self.max_weight and self.max_weight <= self.min_weight:
            raise UserError("The maximum weight must be superior than the minimum weight.")

    @api.multi
    def compute_rate_by_weight(self, weight):
        """
        :param weight: float, value in kg
        :return: returns the rate of the current logistic rate for the specified weight
        """
        self.ensure_one()
        # rounding = self.get_rounding()
        # rest = weight % rounding
        # if rest:
        #     weight = weight - rest + rounding
        if self.type == 'flat_rate':
            return self.rate
        elif self.type == '10kg':
            rest = weight % 10
            if rest:
                weight = weight - rest + 10
            return self.rate * (weight / 10)
        elif self.type == '100kg':
            rest = weight % 100
            if rest:
                weight = weight - rest + 100
            return self.rate * (weight / 100)


class OfLogisticConstraint(models.Model):
    _name = 'of.logistic.constraint'

    name = fields.Char(string="name", compute='_compute_name')
    partner_id = fields.Many2one(
        comodel_name='res.partner', string="Carrier", required=True)
    type = fields.Selection([
        ('weight', 'Maximum weight'),
        ('pallets', 'Up to X pallets'),
        ], string="Constraint type", required=True)
    value = fields.Float(string="Value", required=True)

    @api.depends('partner_id', 'type', 'value')
    def _compute_name(self):
        for constraint in self:
            text = (constraint.type == 'pallets' and "Up to %.0f pallets" or "Max. %.2f kg") % constraint.value
            constraint.name = "%s - %s" % (constraint.partner_id.name, text)

    @api.multi
    def verify_constraints(self, weight=0.0, pallets=0.0):
        """
        :return: return False if all the weight/pallets is within the constraint
                 else return the first constraint to be broken
        """

        for constraint in self:
            if not (not (constraint.type == 'weight' and float_compare(weight, constraint.value, 2) == 1) and not (
                    constraint.type == 'pallets' and float_compare(pallets, constraint.value, 0) == 1)):
                return constraint
        return False
