# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class OFNormeProductTemplate(models.Model):
    _inherit = 'product.template'

    norme_id = fields.Many2one("of.product.norme", string=u"Norme", ondelete="set null")
    description_norme = fields.Text(u"Descriptif de norme", translate=True)

    @api.multi
    @api.onchange('norme_id')
    def _onchange_norme_id(self):
        for product_tmpl in self:
            if product_tmpl.norme_id:
                product_tmpl.description_norme = product_tmpl.norme_id.description
            else:
                product_tmpl.description_norme = None


class OFNormeProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    @api.onchange('norme_id')
    def _onchange_norme_id(self):
        for product in self:
            if product.norme_id:
                product.description_norme = product.norme_id.description
            else:
                product.description_norme = None


class OFProductNorme(models.Model):
    _name = 'of.product.norme'
    _order = 'name'

    name = fields.Char(string=u"Code")
    libelle = fields.Char(string=u"Libellé", translate=True)
    description = fields.Text(string=u"Description", translate=True)
    active = fields.Boolean(string=u"Active", default=True)
    display_docs = fields.Boolean(string=u"Afficher en impression", default=True)

    @api.multi
    def write(self,vals):
        if 'description' in vals:
            # mettre à jour la description_norme des produits si celle-ci est la même que celle de leur norme associée.
            # càd si elle n'a pas été modifiéee
            product_obj = self.env['product.template']
            prods_to_update = self.env['product.template']
            for norme in self:
                # différentes normes avec différentes descriptions peuvent être modifiées pour avoir la même description
                products = product_obj.search([('norme_id','=',norme.id)])
                for prod in products:
                    if prod.description_norme == norme.description:
                        prods_to_update += prod
        super(OFProductNorme,self).write(vals)
        if 'description' in vals:
            prods_to_update.write({'description_norme': vals['description']})
        return True

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
