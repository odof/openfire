# -*- coding: utf-8 -*-

from odoo import models, fields


class OFSaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    group_product_variant_specific_price = fields.Selection(
        group='base.group_portal,base.group_user,base.group_public,of_website_sale.group_portal_b2c')
