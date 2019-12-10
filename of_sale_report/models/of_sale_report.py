# -*- coding: utf-8 -*-

from odoo import api, fields, models

class SaleOrder(models.Model):
    _inherit = "sale.order"

    of_date_de_pose = fields.Date(u'Date de pose prévisionnelle')

class OFSaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    of_rapport_sur_mesure = fields.Selection(
        [('fabricant', "Rapports fabricant"),
         ('revendeur', "Rapports revendeur"),
         ('tous', "Tous les rapports")],
        string=u"(OF) Type de rapports", required=True, default='tous',
        help=u"Donne l'accès aux rapport sur mesure")

    @api.multi
    def set_of_rapport_sur_mesure_defaults(self):
        return self.env['ir.values'].sudo().set_default('sale.config.settings', 'of_rapport_sur_mesure', self.of_rapport_sur_mesure)

class AccountMove(models.Model):
    _inherit = 'account.move'

    of_date_due = fields.Date(string=u"Date d'échéance", compute="_compute_date_due", store=True)

    @api.depends('line_ids', 'line_ids.date_maturity', 'journal_id', 'journal_id.type')
    def _compute_date_due(self):
        """
        Calcule la date d'échéance en fonction du type de journal.
        """
        for move in self:
            move_lines = False
            if move.journal_id.type == 'sale':
                move_lines = move.line_ids.filtered(lambda ml: ml.account_id.user_type_id.type == 'receivable')
            elif move.journal_id.type == 'purchase':
                move_lines = move.line_ids.filtered(lambda ml: ml.account_id.user_type_id.type == 'payable')
            if move_lines:
                move.of_date_due = max(move_lines.mapped('date_maturity'))
