# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields


class Website(models.Model):
    _inherit = 'website'

    def get_current_pricelist(self):
        if self.env.user.of_pricelist_id:
            return self.env.user.of_pricelist_id
        else:
            return super(Website, self).get_current_pricelist()
