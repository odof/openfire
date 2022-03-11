# -*- coding: utf-8 -*-

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp


class OfProductBrand(models.Model):
    _inherit = 'of.product.brand'

    note_maj = fields.Text(
        string=u"Notes de mise à jour",
        help=u"Ce champ est à destination des distributeurs et permet de transmettre des informations "
             u"sur l'état des tarifs")

    datastore_location_id = fields.Many2one(
        comodel_name='stock.location', string="Diffuser le stock", domain="[('usage', '=', 'internal')]")
    datastore_stock_user_ids = fields.Many2many(comodel_name='res.users', string="Restreindre par client")

    @api.model
    def of_access_stocks(self, brand_id):
        current_uid = self.env.uid
        brand = self.search([('id', '=', brand_id)])
        if not brand or not brand.datastore_location_id:
            return False
        return not brand.datastore_stock_user_ids or current_uid in brand.datastore_stock_user_ids._ids


class ProductProduct(models.Model):
    _inherit = 'product.product'

    of_template_image = fields.Binary(related='product_tmpl_id.image', string=u"Image du modèle")


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    of_stock_informations = fields.Text(string="Informations de stock")
    prochain_tarif = fields.Float(
        string=u"Prochain tarif", digits=dp.get_precision('Product Price'), default=0.0)
    date_prochain_tarif = fields.Date(string=u"Date du prochain tarif")

    @api.multi
    def of_datastore_get_quantities(self):
        self.ensure_one()
        product = self.with_context(location=self.brand_id.datastore_location_id.id)
        return\
            product.qty_available - product.outgoing_qty,\
            product.of_stock_informations or "Aucune information"
