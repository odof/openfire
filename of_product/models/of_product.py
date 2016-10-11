# -*- coding: utf-8 -*-

from openerp import api, models, fields
import openerp.addons.decimal_precision as dp

class product_product(models.Model):
    _inherit = "product.product"

    of_frais_port = fields.Float(string='Frais de port', digits_compute=dp.get_precision('Product Price'), help="Frais de port")


class of_product_template(models.Model):
    _inherit = "product.template"

    of_frais_port = fields.Float('Frais de port', compute='_compute_of_frais_port', digits_compute=dp.get_precision('Product Price'),
        inverse = '_set_of_frais_port', store=True,
        help=u"Frais de port.\nSi vous le modifier ici, il sera imposé à toutes les variantes.\nPour ne le modifier que pour une variante, modifiez le dans les variantes d'articles.")

    @api.depends('product_variant_ids', 'product_variant_ids.of_frais_port')
    def _compute_of_frais_port(self):
        for template in self:
            frais_port = ""
            identique = True
            for variantes in template.product_variant_ids:
                if frais_port == "":
                    frais_port = variantes.of_frais_port
                elif frais_port != variantes.of_frais_port:
                    template.of_frais_port = 0.0
                    identique = False
                    break
            if identique:
                template.of_frais_port = frais_port

    @api.one
    def _set_of_frais_port(self):
        #if len(self.product_variant_ids) == 1:
        self.product_variant_ids.write({'of_frais_port': self.of_frais_port})
