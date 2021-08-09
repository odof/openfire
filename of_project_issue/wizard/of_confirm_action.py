# -*- coding: utf-8 -*-

from odoo import api, models, fields

from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime


class OfConfirmAction(models.TransientModel):
    _name = 'of.confirm.action'

    project_issue_id = fields.Many2one('project.issue', string="SAV")
    type = fields.Selection([('sale', 'Sale'),('purchase', 'Purchase')], string="Type", readonly=True)

    @api.multi
    def confirm_open_purchase_order(self):
        # Selon qu'il ait été demandé de générer des CC ou des CF on appelle la fonction correspondante
        if self.type == 'sale':
            return self.project_issue_id.with_context(confirmed=True).open_sale_order()
        elif self.type == 'purchase':
            return self.project_issue_id.with_context(confirmed=True).open_purchase_order()
