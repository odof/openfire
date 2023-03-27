# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api


class SaleConfigSettings(models.TransientModel):
    _inherit = 'sale.config.settings'

    group_show_price_subtotal = fields.Boolean(group='base.group_portal,base.group_user')
    group_show_price_total = fields.Boolean(group='base.group_portal,base.group_user')


class WebsiteConfigSettings(models.TransientModel):
    _inherit = 'website.config.settings'

    group_of_validate_order_from_portal = fields.Boolean(
        string='Activer la validation de commande depuis le portail',
        implied_group='of_website_portal.group_of_validate_order_from_portal',
        group='base.group_portal,base.group_user')


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
        ('order_validation', u"À la validation de la commande"),
    ], string=u"(OF) Création utilisateur portail", default='manual', required=True)

    @api.multi
    def set_of_create_portal_users_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'base.config.settings', 'of_create_portal_users', self.of_create_portal_users)


class OFInterventionSettings(models.TransientModel):
    _inherit = 'of.intervention.settings'

    @api.model
    def _auto_init(self):
        super(OFInterventionSettings, self)._auto_init()
        self.env['ir.values'].set_default('of.intervention.settings', 'website_edit_days_limit', 7)

    website_edit_days_limit = fields.Integer(string=u"(OF) Limite d'annulation", default=7)

    @api.multi
    def set_website_edit_days_limit_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'website_edit_days_limit', self.website_edit_days_limit)
