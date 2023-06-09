# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api, _


class WebsiteConfigSettings(models.TransientModel):
    _inherit = 'website.config.settings'

    @api.model
    def _auto_init(self):
        res = super(WebsiteConfigSettings, self)._auto_init()
        if not self.env['ir.values'].get_default('website.config.settings', 'of_picking_rollback_delay'):
            # par défaut 24h
            self.env['ir.values'].sudo().set_default('website.config.settings', 'of_picking_rollback_delay', 1440)
        return res

    of_picking_rollback_delay = fields.Integer(string=u"(OF) Délais de modification des BR")

    @api.onchange('of_picking_rollback_delay')
    def _onhcnage_of_picking_rollback_delay(self):
        if self.of_picking_rollback_delay and self.of_picking_rollback_delay < 0:
            self.of_picking_rollback_delay = 0

    @api.multi
    def set_of_picking_rollback_delay_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'website.config.settings', 'of_picking_rollback_delay', self.of_picking_rollback_delay)
