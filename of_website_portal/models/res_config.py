# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


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
