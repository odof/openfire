# -*- coding: utf-8 -*-

from odoo import api, fields, models


class OFSaleOrderAddQuoteWizard(models.TransientModel):
    _name = 'of.sale.order.add.quote.wizard'
    _description = "Assistant d'ajout de devis complémentaire"

    order_id = fields.Many2one(comodel_name='sale.order', string=u"Bon de commande")
    quote_id = fields.Many2one(comodel_name='sale.order', string=u"Devis à ajouter")
    addable_quote_ids = fields.Many2many(comodel_name='sale.order', compute='_compute_addable_quote_ids')

    @api.depends('order_id')
    def _compute_addable_quote_ids(self):
        for rec in self:
            if rec.order_id:
                rec.addable_quote_ids = self.env['sale.order'].search(
                    [('partner_invoice_id', '=', rec.order_id.partner_invoice_id.id),
                     ('partner_shipping_id', '=', rec.order_id.partner_shipping_id.id),
                     ('company_id', '=', rec.order_id.company_id.id),
                     ('state', 'in', ['draft', 'sent'])])
            else:
                rec.addable_quote_ids = False

    @api.multi
    def add_quote(self):
        self.ensure_one()
        # On copie les lignes du devis dans le bon de commande
        for line in self.quote_id.order_line:
            new_line = line.copy(
                {'order_id': self.order_id.id,
                 'name': line.name + u"\n\nLigne ajoutée depuis le devis complémentaire %s" % self.quote_id.name})
            # On change le nom des lignes de kit
            if new_line.of_is_kit:
                for kit_line in new_line.kit_id.kit_line_ids:
                    kit_line.name = kit_line.name + u" - Ligne ajoutée depuis le devis complémentaire %s" \
                                    % self.quote_id.name
                    for move in kit_line.procurement_ids.mapped('move_ids'):
                        move.name = move.name + u" - Ligne ajoutée depuis le devis complémentaire %s" \
                                    % self.quote_id.name
        # On annule le devis
        self.quote_id.action_cancel()
        return True
