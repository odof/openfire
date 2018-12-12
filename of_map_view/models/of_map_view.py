# -*- coding: utf-8 -*-

from odoo import api, models, fields

class OFMapViewMixin(models.AbstractModel):
    _name = "of.map.view.mixin"

    @api.model
    def get_color_map(self):
        raise NotImplementedError("A class inheriting from this one must implement a 'get_color_map' function")

class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = ["res.partner","of.map.view.mixin"]

    @api.model
    def get_color_map(self):
        """
        no color for partner maps
        """
        return None