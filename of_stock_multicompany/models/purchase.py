# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.model
    def _default_picking_type(self):
        type_obj = self.env['stock.picking.type']
        company_id = self.env.context.get('company_id') or self.env.user.company_id.id
        company = self.env['res.company'].browse(company_id)
        types = type_obj.search([('code', '=', 'incoming'), ('warehouse_id.company_id', '=', company_id)])
        partner_ids = [company.partner_id.id]

        # Filtres des règles par société de l'entrepôt
        while not types and company:
            # Recherche en remontant les sociétés parentes.
            # Si aucune règle n'est trouvée, on finit par une recherche sur société vide.
            company = company.parent_id
            partner_ids.append(company.partner_id.id)
            types = type_obj.search([('code', '=', 'incoming'), ('warehouse_id.company_id', '=', company.id)])

        # Filtre des règles par adresse de l'entrepôt
        for pid in partner_ids:
            if len(types) <= 1:
                break
            types = types.filtered(lambda t: t.warehouse_id.partner_id.id == pid) or types
        return types[:1]

    picking_type_id = fields.Many2one(default=lambda self: self._default_picking_type())
