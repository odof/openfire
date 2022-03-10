# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    of_date_de_pose = fields.Date(u'Date de pose prévisionnelle')


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.multi
    def _prepare_order_line_procurement(self, group_id=False):
        res = super(SaleOrderLine, self)._prepare_order_line_procurement(group_id)
        if isinstance(res, dict) and self.order_id.of_date_de_pose:
            res['date_planned'] = self.order_id.of_date_de_pose
        return res

    @api.multi
    def update_procurement_date_planned(self):
        for order_line in self:
            if order_line.order_id.of_date_de_pose and order_line.procurement_ids:
                order_line.procurement_ids.write({'date_planned': order_line.order_id.of_date_de_pose})
                moves = order_line.procurement_ids.mapped('move_ids')
                if moves:
                    moves.write({'date_expected': order_line.order_id.of_date_de_pose})
                    pickings = order_line.procurement_ids.mapped('move_ids').mapped('picking_id')
                    if pickings:
                        pickings.write({'min_date': order_line.order_id.of_date_de_pose})


class OFSaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    of_rapport_sur_mesure = fields.Selection(
        [('fabricant', "Rapports fabricant"),
         ('revendeur', "Rapports revendeur"),
         ('tous', "Tous les rapports")],
        string=u"(OF) Type de rapports", required=True, default='tous',
        help=u"Donne l'accès aux rapport sur mesure")

    of_sale_order_installation_date_control = fields.Boolean(
        string=u"(OF) Contrôle de date de pose",
        help=u"Activer le contrôle de date de pose à la validation des commandes")

    @api.multi
    def set_of_rapport_sur_mesure_defaults(self):
        return self.env['ir.values'].sudo().set_default('sale.config.settings', 'of_rapport_sur_mesure', self.of_rapport_sur_mesure)

    @api.multi
    def set_of_sale_order_installation_date_control(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_sale_order_installation_date_control',
            self.of_sale_order_installation_date_control)


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
