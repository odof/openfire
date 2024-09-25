# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import itertools
import math

from odoo import api, models, fields, _


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.model
    def _auto_init(self):
        cr = self.env.cr
        cr.execute(
            "SELECT 1 "
            "FROM information_schema.columns "
            "WHERE table_name = '%s' "
            "AND column_name = 'of_total_eco_contribution'" % self._table)
        if not bool(cr.fetchall()):
            cr.execute(
                "ALTER TABLE %s ADD COLUMN of_total_eco_contribution NUMERIC" % self._table
            )
        res = super(AccountInvoice, self)._auto_init()
        return res

    of_total_eco_contribution = fields.Float(
        string=u"Dont éco-contribution PMCB", compute='_compute_of_total_eco_contribution')

    @api.depends('invoice_line_ids.of_total_eco_contribution')
    def _compute_of_total_eco_contribution(self):
        for record in self:
            record.of_total_eco_contribution = sum(record.mapped('invoice_line_ids.of_total_eco_contribution'))

    def invoice_line_move_line_get(self):
        res = super(AccountInvoice, self).invoice_line_move_line_get()
        copy = [x for x in res]
        for aml in copy:
            line = self.invoice_line_ids.filtered(lambda il: il.id == aml['invl_id'])
            if line and line.of_total_eco_contribution:
                contribution = line.product_id.of_eco_contribution_id
                # on a de l'éco-contribution sur la ligne et l'éco-organisme a un compte comptable renseigné
                # on a donc une nouvelle ligne dans la pièce comptable pour l'éco-contribution
                if contribution.organism_id.account_id:
                    analytic_tag_ids = [(4, analytic_tag.id, None) for analytic_tag in line.analytic_tag_ids]
                    res_aml_index = res.index(aml)
                    move_line_dict = {
                        'invl_id': line.id,
                        'type': 'src',
                        'name': line.name.split('\n')[0][:64],
                        'price_unit': line.of_total_eco_contribution,
                        'quantity': 1.0,
                        'price': line.of_total_eco_contribution,
                        'account_id': contribution.organism_id.account_id.id,
                        'product_id': line.product_id.id,
                        'uom_id': line.uom_id.id,
                        'account_analytic_id': line.account_analytic_id.id,
                        # 'tax_ids': tax_ids,
                        'invoice_id': self.id,
                        'analytic_tag_ids': analytic_tag_ids
                    }
                    res[res_aml_index]['price'] = res[res_aml_index]['price'] - line.of_total_eco_contribution
                    res.append(move_line_dict)
        return res

class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    @api.model
    def _auto_init(self):
        cr = self.env.cr
        cr.execute(
            "SELECT 1 "
            "FROM information_schema.columns "
            "WHERE table_name = '%s' "
            "AND column_name = 'of_total_eco_contribution'" % self._table)
        if not bool(cr.fetchall()):
            cr.execute(
                "ALTER TABLE %s ADD COLUMN of_total_eco_contribution NUMERIC" % self._table
            )
            cr.execute(
                "ALTER TABLE %s ADD COLUMN of_unit_eco_contribution NUMERIC" % self._table
            )
        res = super(AccountInvoiceLine, self)._auto_init()
        return res

    of_total_eco_contribution = fields.Float(
        string=u"Montant éco-contribution", compute='_compute_of_total_eco_contribution', store=True)
    of_unit_eco_contribution = fields.Float(
        string=u"Montant unitaire éco-contribution", compute='_compute_of_total_eco_contribution', store=True)
    of_eco_contribution_id = fields.Many2one(
        comodel_name='of.eco.contribution', string=u"Éco-contribution", compute='_compute_of_eco_contribution_id',
        store=True)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        res = super(AccountInvoiceLine, self)._onchange_product_id()
        if not self.env['ir.values'].sudo().get_default(
                'account.config.settings', 'of_eco_contribution_price_included'):
            # L'éco-contribution doit être incluse dans le prix unitaire
            self.price_unit = self.price_unit + self.of_unit_eco_contribution
        return res

    @api.depends('product_id', 'quantity', 'uom_id', 'kit_id', 'of_is_kit')
    def _compute_of_total_eco_contribution(self):
        for record in self:
            contribution = record.product_id.of_eco_contribution_id
            if record.of_is_kit:
                record.of_unit_eco_contribution = record.kit_id.of_total_eco_contribution
                record.of_total_eco_contribution = record.kit_id.of_total_eco_contribution * record.quantity
            elif record.product_id.of_eco_contribution_id:
                if record.product_id.of_packaging_unit and contribution.type in ['ton', 'unit']:
                    qty = int(math.ceil(round(record.quantity / record.product_id.of_packaging_unit, 3)))
                else:
                    original_uom = record.product_id.uom_id
                    current_uom = record.uom_id
                    qty = current_uom._compute_quantity(record.quantity, original_uom, round=False)
                if contribution.type == 'ton':
                    eco_contribution = contribution.price * record.product_id.weight / 1000.0
                else:
                    eco_contribution = contribution.price
                record.of_unit_eco_contribution = eco_contribution
                record.of_total_eco_contribution = qty * eco_contribution

    @api.depends('of_total_eco_contribution', 'product_id')
    def _compute_of_eco_contribution_id(self):
        for record in self:
            record.of_eco_contribution_id = record.product_id.of_eco_contribution_id

    @api.depends('kit_id.kit_line_ids', 'of_unit_eco_contribution')
    def _compute_price_comps(self):
        add_eco = not self.env['ir.values'].sudo().get_default(
                'account.config.settings', 'of_eco_contribution_price_included')
        for line in self:
            if line.of_is_kit:
                uc_price = 0
                uc_cost = 0
                if line.kit_id:
                    for comp in line.kit_id.kit_line_ids:
                        uc_price += comp.price_unit * comp.qty_per_kit
                        uc_cost += comp.cost_unit * comp.qty_per_kit
                if add_eco:
                    uc_price += line.of_unit_eco_contribution
                line.price_comps = uc_price
                line.cost_comps = uc_cost


class OfAccountInvoiceKit(models.Model):
    _inherit = 'of.invoice.kit'

    @api.model
    def _auto_init(self):
        cr = self.env.cr
        cr.execute(
            "SELECT 1 "
            "FROM information_schema.columns "
            "WHERE table_name = '%s' "
            "AND column_name = 'of_total_eco_contribution'" % self._table)
        if not bool(cr.fetchall()):
            cr.execute(
                "ALTER TABLE %s ADD COLUMN of_total_eco_contribution NUMERIC" % self._table
            )
        res = super(OfAccountInvoiceKit, self)._auto_init()
        return res

    of_total_eco_contribution = fields.Float(
        string=u"Montant éco-contribution", compute='_compute_of_total_eco_contribution', store=True)

    @api.depends('kit_line_ids.of_total_eco_contribution')
    def _compute_of_total_eco_contribution(self):
        for record in self:
            record.of_total_eco_contribution = sum(record.kit_line_ids.mapped('of_total_eco_contribution'))

    @api.multi
    @api.depends('kit_line_ids', 'of_total_eco_contribution')
    def _compute_price_comps(self):
        add_eco = not self.env['ir.values'].sudo().get_default(
                'account.config.settings', 'of_eco_contribution_price_included')
        for kit in self:
            price = 0.0
            cost = 0.0
            if kit.kit_line_ids:
                for comp in kit.kit_line_ids:
                    price += comp.price_unit * comp.qty_per_kit
                    cost += comp.cost_unit * comp.qty_per_kit
                if add_eco:
                    price += kit.of_total_eco_contribution
                kit.price_comps = price
                kit.cost_comps = cost


class OfAccountInvoiceKitLine(models.Model):
    _inherit = 'of.invoice.kit.line'

    @api.model
    def _auto_init(self):
        cr = self.env.cr
        cr.execute(
            "SELECT 1 "
            "FROM information_schema.columns "
            "WHERE table_name = '%s' "
            "AND column_name = 'of_total_eco_contribution'" % self._table)
        if not bool(cr.fetchall()):
            cr.execute(
                "ALTER TABLE %s ADD COLUMN of_total_eco_contribution NUMERIC" % self._table
            )
            cr.execute(
                "ALTER TABLE %s ADD COLUMN of_unit_eco_contribution NUMERIC" % self._table
            )
        res = super(OfAccountInvoiceKitLine, self)._auto_init()
        return res

    of_total_eco_contribution = fields.Float(
        string=u"Montant éco-contribution", compute='_compute_of_total_eco_contribution', store=True)
    of_unit_eco_contribution = fields.Float(
        string=u"Montant unitaire éco-contribution", compute='_compute_of_total_eco_contribution', store=True)

    @api.depends('product_id', 'qty_per_kit', 'product_uom_id', 'kit_id.invoice_line_id.quantity')
    def _compute_of_total_eco_contribution(self):
        for record in self:
            if record.product_id.of_eco_contribution_id:
                contribution = record.product_id.of_eco_contribution_id
                original_uom = record.product_id.uom_id
                current_uom = record.product_uom_id
                base_qty = record.qty_per_kit * record.kit_id.invoice_line_id.quantity
                qty = current_uom._compute_quantity(base_qty, original_uom, round=False)
                if contribution.type == 'ton':
                    eco_contribution = contribution.price * record.product_id.weight / 1000.0
                else:
                    eco_contribution = contribution.price
                record.of_unit_eco_contribution = eco_contribution
                record.of_total_eco_contribution = qty * eco_contribution
