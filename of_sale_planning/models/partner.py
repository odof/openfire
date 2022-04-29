# -*- coding: utf-8 -*-

from odoo import api, models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    of_invoice_policy = fields.Selection(selection_add=[('intervention', u'Quantités planifiées')])
    of_is_planning_warn = fields.Boolean(string=u"Avertissement interventions")

    @api.depends('of_is_planning_warn')
    def _compute_of_is_warn(self):
        has_warn = self.filtered(lambda p: p.of_is_planning_warn)
        # `has_warn.of_is_warn = True` ne fonctionne pas car expected singleton
        for partner in has_warn:
            partner.of_is_warn = True
        partners_left = self - has_warn
        super(ResPartner, partners_left)._compute_of_is_warn()
