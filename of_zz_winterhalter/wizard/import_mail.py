# -*- coding: utf-8 -*-

from openerp import models, api

class of_gesdoc_import(models.TransientModel):
    _inherit = 'of.gesdoc.import'

    def import_data_obj(self, data, obj):
        result = super(of_gesdoc_import, self).import_data_obj(data, obj)
        if obj._name == 'project.issue':
            result.update({field[3:]: data[field] for field in ('pi_of_actions_realisees','pi_of_actions_eff') if field in data})
        return result
