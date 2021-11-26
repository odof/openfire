# -*- coding: utf-8 -*-

from odoo import api, models, fields


class OFMakePOValidationWizard(models.TransientModel):
    _name = 'of.make.po.validation.wizard'

    message = fields.Text(string=u"Message", readonly=True)
    service_id = fields.Many2one(
        string=u"Demande d'intervention", comodel_name='of.service', required=True)

    @api.multi
    def validate(self):
        self.ensure_one()
        return self.service_id.with_context(of_make_po_validated=True).make_purchase_order()
