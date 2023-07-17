# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api


class WebsiteConfigSettings(models.TransientModel):
    _inherit = 'website.config.settings'

    @api.model
    def _auto_init(self):
        res = super(WebsiteConfigSettings, self)._auto_init()
        if not self.env['ir.values'].get_default(
                'website.config.settings', 'of_picking_rollback_delay_minutes_supplier'):
            # par défaut 24h
            self.env['ir.values'].sudo().set_default(
                'website.config.settings', 'of_picking_rollback_delay_minutes_supplier', 1440)
        return res

    of_picking_rollback_delay_minutes_supplier = fields.Integer(
        string=u"(OF) Délais de modification des BR pour les fournisseurs")

    @api.onchange('of_picking_rollback_delay_minutes_supplier')
    def _onchange_of_picking_rollback_delay_minutes_supplier(self):
        if self.of_picking_rollback_delay_minutes_supplier and self.of_picking_rollback_delay_minutes_supplier < 0:
            self.of_picking_rollback_delay_minutes_supplier = 0

    @api.multi
    def set_of_picking_rollback_delay_minutes_supplier_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'website.config.settings',
            'of_picking_rollback_delay_minutes_supplier',
            self.of_picking_rollback_delay_minutes_supplier)
