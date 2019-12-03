# -*- encoding: utf-8 -*-

from odoo import models, api

class OFWebWidgetsUtils(models.Model):
    _name = "of.web.widgets.utils"

    @api.model
    def est_actif(self, record_id, model_name):
        self = self.sudo()
        model_obj = self.env[model_name]
        if 'active' not in model_obj._fields:
            return True
        return model_obj.browse(record_id).active
