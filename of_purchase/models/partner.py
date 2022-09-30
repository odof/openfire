# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    of_br_count = fields.Integer(string=u"Réceptions", compute="_compute_of_br_count")

    def _compute_of_br_count(self):
        picking_obj = self.env['stock.picking']
        for partner in self:
            partner.of_br_count = picking_obj.search_count(
                [('of_customer_id', '=', partner.id), ('of_location_usage', '=', 'supplier')])

    @api.multi
    def _purchase_invoice_count(self):
        super(ResPartner, self)._purchase_invoice_count()
        all_partners = self.with_context(active_test=False).search([('id', 'child_of', self.ids)])
        all_partners.read(['parent_id'])

        purchase_order_groups = self.env['purchase.order'].read_group(
            domain=[('partner_id', 'in', all_partners.ids)],
            fields=['partner_id'], groupby=['partner_id']
        )

        for group in purchase_order_groups:
            partner = self.browse(group['partner_id'][0])
            while partner:
                if partner in self:
                    # On assigne purchase_order_count sans le += contrairement à la fonction originale,
                    # car elle est appelée dans le super. Du coup, on souhaite écraser la valeur existante
                    partner.purchase_order_count = group['partner_id_count']
                partner = partner.parent_id

        # On réapplique la deuxième étape de la fonction pour ajouter les avoir fournisseurs
        supplier_invoice_groups = self.env['account.invoice'].read_group(
            domain=[('partner_id', 'in', all_partners.ids),
                    ('type', '=', 'in_refund')],
            fields=['partner_id'], groupby=['partner_id']
        )
        for group in supplier_invoice_groups:
            partner = self.browse(group['partner_id'][0])
            while partner:
                if partner in self:
                    partner.supplier_invoice_count += group['partner_id_count']
                partner = partner.parent_id

    @api.multi
    def action_view_picking(self):
        action = self.env.ref('of_purchase.of_purchase_open_picking').read()[0]
        action['domain'] = [('of_customer_id', 'in', self._ids)]
        return action
