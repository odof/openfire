# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    of_cee_invoice_template = fields.Selection(
        selection=[('of_cee.of_cee_edf_invoice', u"Modèle EDF"),
                   ('of_cee.of_cee_engie_invoice', u"Modèle Engie")], string=u"Modèle de facture CEE")
