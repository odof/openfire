# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OfAccountInvoice(models.Model):
    _inherit = "account.invoice"

    of_contract_id = fields.Many2one('of.contract', string="(OF) Contrat")


class OfAccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    of_contract_id = fields.Many2one('of.contract', string="(OF) Contrat")
    of_contract_product_id = fields.Many2one('of.contract.product', string="(OF) Article contrat")
    of_contract_line_id = fields.Many2one('of.contract.line', string="(OF) Ligne de contrat")

