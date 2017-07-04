# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class OFNormeProductTemplate(models.Model):
    _inherit = 'product.template'

    norme_id = fields.Many2one("of.product.norme",string="Norme",ondelete="set null")
    description_norme = fields.Text("Descriptif de norme")

    @api.multi
    @api.onchange('norme_id')
    def _onchange_norme_id(self):
        for product_tmpl in self:
            if product_tmpl.norme_id:
                product_tmpl.description_norme = product_tmpl.norme_id.description
            else:
                product_tmpl.description_norme = None

class OFProductNorme(models.Model):
    _name = 'of.product.norme'

    name = fields.Char(string="Code")
    libelle = fields.Char(string="Libellé")
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Active", default=True)
    display_docs = fields.Boolean("Afficher en impression")

class OFNormeSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        res = super(OFNormeSaleOrderLine,self).product_id_change()

        product = self.product_id.with_context(
            lang=self.order_id.partner_id.lang,
            partner=self.order_id.partner_id.id,
        )
        if product and product.description_norme and product.norme_id and product.norme_id.active and product.norme_id.display_docs:
            name = self.name
            name += u'\nConforme à la norme %s : %s' % (product.norme_id.name, product.description_norme)
            self.update({'name': name})
        return res

class OFNormeAccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    @api.onchange('product_id')
    def _onchange_product_id(self):
        res = super(OFNormeAccountInvoiceLine,self)._onchange_product_id()
        product = self.product_id.with_context(
            lang=self.invoice_id.partner_id.lang,
            partner=self.invoice_id.partner_id.id,
        )
        if product and product.description_norme and product.norme_id and product.norme_id.active and product.norme_id.display_docs:
            self.name += u'\nConforme à la norme %s : %s' % (product.norme_id.name, product.description_norme)
        return res
