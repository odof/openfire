# -*- coding: utf-8 -*-

import math

from odoo import models, fields, api
from odoo.tools.misc import formatLang


class ProductTemplate(models.Model):
    _inherit = "product.template"

    of_packaging_unit = fields.Float(string=u"Conditionnement")
    of_packaging_type = fields.Char(string=u"Type de conditionnement")
    of_uom_id_display = fields.Many2one(related='uom_id', readonly=True)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_packaging_unit = fields.Char(string=u"Conditionnement", compute='_compute_of_packaging_unit')
    of_display_required_units = fields.Boolean(string=u"Affichage des informations de conditionnement")
    of_force_qty = fields.Boolean(string=u"Forcer la quantité")
    of_display_force_qty = fields.Boolean(string=u"Affichage du paramètre pour forcer les quantités")

    @api.multi
    @api.depends('product_id', 'product_uom_qty')
    def _compute_of_packaging_unit(self):
        for rec in self:
            if rec.product_id and rec.product_id.of_packaging_unit and rec.product_uom_qty:
                required_units = int(math.ceil(rec.product_uom_qty / rec.product_id.of_packaging_unit))
                packaging_unit_str = formatLang(self.env, rec.product_id.of_packaging_unit, 2)

                required_units_str = str(required_units)
                if rec.product_id.of_packaging_type:
                    required_units_str = u"%s %s" % (required_units, rec.product_id.of_packaging_type)
                rec.of_packaging_unit = u"%s x %s %s" % \
                                        (required_units_str, packaging_unit_str, rec.product_id.uom_id.name)
            else:
                rec.of_packaging_unit = ""

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        res = super(SaleOrderLine, self).product_id_change()
        if self.product_id and self.product_id.of_packaging_unit:
            self.product_uom_qty = False
            self.of_display_force_qty = True
        else:
            self.of_display_force_qty = False
        self.of_display_required_units = False
        return res

    @api.multi
    @api.onchange('product_uom_qty')
    def _onchange_product_uom_qty(self):
        res = super(SaleOrderLine, self)._onchange_product_uom_qty()
        if self.product_id and self.product_id.of_packaging_unit and self.product_uom_qty:
            required_units = int(math.ceil(self.product_uom_qty / self.product_id.of_packaging_unit))
            self.of_display_required_units = True
            if not self.of_force_qty:
                self.product_uom_qty = required_units * self.product_id.of_packaging_unit

            # Mise à jour de la description
            conditionnement_str = u"Conditionnement : " + self.of_packaging_unit
            desc_lines = self.name.splitlines()
            for i, desc_line in enumerate(desc_lines):
                if u"Conditionnement : " in desc_line:
                    desc_lines[i] = conditionnement_str
                    break
            else:
                desc_lines.append(conditionnement_str)
            self.name = "\n".join(desc_lines)
        else:
            self.of_display_required_units = False
        return res
