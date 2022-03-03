# -*- coding: utf-8 -*-

from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # if both of_datastore_supplier and of_datastore_product are installed, we want these fields not to be readonly
    prochain_tarif = fields.Float(readonly=False)
    date_prochain_tarif = fields.Date(readonly=False)
