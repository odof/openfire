# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import math

from odoo import api, models, fields, _


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

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

    of_total_eco_contribution = fields.Float(
        string=u"Montant éco-contribution", compute='_compute_of_total_eco_contribution', store=True)
    of_unit_eco_contribution = fields.Float(
        string=u"Montant unitaire éco-contribution", compute='_compute_of_total_eco_contribution', store=True)

    @api.depends('product_id', 'quantity', 'uom_id', 'kit_id', 'of_is_kit')
    def _compute_of_total_eco_contribution(self):
        for record in self:
            contribution = record.product_id.of_eco_contribution_id
            if record.of_is_kit:
                record.of_total_eco_contribution = record.kit_id.of_total_eco_contribution
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


class OfAccountInvoiceKit(models.Model):
    _inherit = 'of.invoice.kit'

    of_total_eco_contribution = fields.Float(
        string=u"Montant éco-contribution", compute='_compute_of_total_eco_contribution', store=True)

    @api.depends('kit_line_ids.of_total_eco_contribution')
    def _compute_of_total_eco_contribution(self):
        for record in self:
            record.of_total_eco_contribution = sum(record.kit_line_ids.mapped('of_total_eco_contribution'))


class OfAccountInvoiceKitLine(models.Model):
    _inherit = 'of.invoice.kit.line'

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
