# -*- coding: utf-8 -*-

from odoo import models, fields

class OfProductBrand(models.Model):
    _inherit = 'of.product.brand'

    note_maj = fields.Text(
        string=u"Notes de mise à jour",
        help=u"Ce champ est à destination des distributeurs et permet de transmettre des information sur l'état des tarifs")
