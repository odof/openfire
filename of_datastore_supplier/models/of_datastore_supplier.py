# -*- coding: utf-8 -*-

from odoo import models, fields

class of_import_note(models.Model):
    _name = 'of.import.note'

    brand_id = fields.Many2one('of.product.brand', required=True)
    name = fields.Char(related='brand_id.name', string="Name")
    note = fields.Text(string='Notes de MAJ')

    _sql_constraints = [
        ('name_id_unique', 'unique (brand_id)', u"Une note existe déjà pour cette marque"),
    ]

class ProductSupplierInfo(models.Model):
    _inherit = "product.supplierinfo"

    pp_ht = fields.Float(related='product_id.standard_price')
    of_product_category = fields.Char(related='product_id.categ_id.name')
