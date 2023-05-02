# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api


class BaseConfigSettings(models.TransientModel):
    _inherit = 'base.config.settings'

    @api.model
    def _auto_init(self):
        super(BaseConfigSettings, self)._auto_init()
        if self.env['ir.values'].get_default('base.config.settings', 'of_create_portal_users') is None:
            self.env['ir.values'].set_default('base.config.settings', 'of_create_portal_users', 'manual')

    of_create_portal_users = fields.Selection(selection=[
        ('manual', u"Manuelle"),
        ('contact_creation', u"À la création du contact"),
        ('order_preconfirm', u"À la validation de la commande"),
        ('order_validation', u"A l'enregistrement de la commande"),
    ])

    @api.multi
    def set_of_create_portal_users_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'base.config.settings', 'of_create_portal_users', self.of_create_portal_users)
