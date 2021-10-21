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
    of_packaging_unit_number = fields.Float(
        string=u"Unité de conditionnement", related='product_id.of_packaging_unit', readonly=True)
    of_product_qty_brut = fields.Float(
        string=u"Quantité brute", digits=(12,2),
        help=u"L'Unité de Quantité(s) commandée(s) doit être le m² pour que cela corresponde")
    of_coefficient_marge = fields.Float(
        string=u"Coefficient (en %)", digits=(12,2),
        help=u"Le coefficient s’applique à la quantité brute pour avoir une marge d’erreur ou de perte.")

    @api.multi
    @api.depends('product_id', 'product_uom_qty')
    def _compute_of_packaging_unit(self):
        for rec in self:
            if rec.product_id and rec.product_id.of_packaging_unit and rec.product_uom_qty:
                required_units = int(math.ceil(round(rec.product_uom_qty / rec.product_id.of_packaging_unit, 3)))
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
    @api.onchange('of_packaging_unit_number','of_product_qty_brut','of_coefficient_marge')
    def _onchange_chantier(self):
        if not self.of_force_qty:
            product_uom_qty = 0.0
            if self.product_id and self.of_packaging_unit_number and self.of_product_qty_brut:
                product_uom_qty = self.of_packaging_unit_number * self.of_product_qty_brut
                if self.of_coefficient_marge:
                    product_uom_qty *= 1 + (self.of_coefficient_marge/100)
            if product_uom_qty:
                self.product_uom_qty = product_uom_qty

            # Mise à jour de la description
            surface_str = u"Quantité brute : %s %s" % (self.of_product_qty_brut, self.product_id.of_packaging_type)
            coef_str = u"Marge appliquée : %s%s" % (self.of_coefficient_marge, "%")
            old_desc_lines = self.name and self.name.splitlines() or []
            new_desc_lines = []
            for i, desc_line in enumerate(old_desc_lines):
                if u"Quantité brute : " in desc_line or u"Marge appliquée : " in desc_line:
                    continue
                new_desc_lines.append(desc_line)
            else:
                new_desc_lines.append(surface_str)
                new_desc_lines.append(coef_str)
            self.name = "\n".join(new_desc_lines)

    @api.multi
    @api.onchange('product_uom_qty')
    def _onchange_product_uom_qty(self):
        res = super(SaleOrderLine, self)._onchange_product_uom_qty()
        if self.product_id and self.product_id.of_packaging_unit and self.product_uom_qty:

            if not self.of_force_qty:
                product_uom_qty = 0.0
                if self.of_product_qty_brut:
                    product_uom_qty = self.of_packaging_unit_number * self.of_product_qty_brut
                    if self.of_coefficient_marge:
                        product_uom_qty *= 1 + (self.of_coefficient_marge/100)
                if product_uom_qty:
                    self.product_uom_qty = product_uom_qty

                required_units = int(math.ceil(round(self.product_uom_qty / self.product_id.of_packaging_unit, 3)))
                self.of_display_required_units = True
                self.product_uom_qty = required_units * self.product_id.of_packaging_unit

            else:
                # Si of_force_qty, on supprime les informations de quantités brutes et coef de la description
                old_desc_lines = self.name and self.name.splitlines() or []
                new_desc_lines = []
                for i, desc_line in enumerate(old_desc_lines):
                    if u"Quantité brute : " in desc_line or u"Marge appliquée : " in desc_line:
                        continue
                    new_desc_lines.append(desc_line)
                self.name = "\n".join(new_desc_lines)

            # Mise à jour de la description
            conditionnement_str = u"Conditionnement : " + self.of_packaging_unit
            desc_lines = self.name and self.name.splitlines() or []
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
