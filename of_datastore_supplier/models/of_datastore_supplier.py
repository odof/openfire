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
    datastore_stock_user_ids = fields.Many2many(
        comodel_name='res.users', string="Restreindre par client",
        context={'of_distributor_test': False, 'search_default_of_distributor': True})

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

    def read(self, fields=None, load='_classic_read'):
        if 'standard_price' in fields and 'of_product_user_id' not in self._context:
            self = self.with_context(of_product_user_id=self.env.uid)
        return super(ProductProduct, self).read(fields=fields, load=load)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    of_stock_informations = fields.Text(string="Informations de stock")
    prochain_tarif = fields.Float(
        string=u"Prochain tarif", digits=dp.get_precision('Product Price'), default=0.0)
    date_prochain_tarif = fields.Date(string=u"Date du prochain tarif")

    @api.depends('product_variant_ids', 'product_variant_ids.standard_price')
    def _compute_standard_price(self):
        # Verrou de lecture du prix d'achat.
        # Fonction non utilisée par appel du tarif centralisé
        # Cette protection est à titre préventif et protège en cas d'appel xmlrpc ou d'accès direct à la base centrale
        group = self.env.ref('of_sale.of_group_sale_marge_manager', raise_if_not_found=False)
        user = self.env.user
        if user.of_is_distributor and group and not user.has_group(
                'of_sale.of_group_sale_marge_manager'):
            for template in self:
                template.standard_price = 0.0
        else:
            super(ProductTemplate, self)._compute_standard_price()

    @api.multi
    def of_datastore_get_quantities(self):
        self.ensure_one()
        product = self.with_context(location=self.brand_id.datastore_location_id.id)
        return\
            product.qty_available - product.outgoing_qty,\
            product.of_stock_informations or "Aucune information"


class ProductSupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    def _convert_to_cache(self, values, update=False, validate=True):
        """
        Interdiction de lire le prix d'achat pour les distributeurs s'ils n'appartiennent pas au groupe des marges
        """
        if 'price' in values:
            group = self.env.ref('of_sale.of_group_sale_marge_manager', raise_if_not_found=False)
            user = self.env.user
            if user.of_is_distributor and group and not user.has_group(
                    'of_sale.of_group_sale_marge_manager'):
                values['price'] = 0
        return super(ProductSupplierInfo, self)._convert_to_cache(values, update=update, validate=validate)
