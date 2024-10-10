# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from of_datastore_product import DATASTORE_IND

from odoo import api, fields, models


# Création/édition d'objets incluant un article centralisé
class OfDatastoreProductReference(models.AbstractModel):
    _name = 'of.datastore.product.reference'

    @api.model
    def create(self, vals):
        # par défaut .get() retourne None si la clef n'existe pas, et None == -1
        # Gestion des many2one
        if vals.get('product_id', 0) < 0:
            vals['product_id'] = self.env['product.product'].browse(vals['product_id']).of_datastore_import().id

        # Gestion des many2many
        if vals.get('product_ids') and vals['product_ids'][0][2]:
            res = []
            product_ids = vals['product_ids'][0][2]
            ds_products = self.env['product.product'].browse([pid for pid in product_ids if pid < 0])

            # On appelle of_datastore_import() ici plutôt que dans le for
            # pour éviter d'appeler trop souvent la base centralisée
            products = ds_products.of_datastore_import()
            ds_products_dict = {p.of_datastore_res_id: p.id for p in products}

            for pid in product_ids:
                if pid < 0:
                    pid = ds_products_dict[-pid % DATASTORE_IND]
                res.append(pid)
            vals['product_ids'] = [[6, 0, res]]

        return super(OfDatastoreProductReference, self).create(vals)

    @api.multi
    def write(self, vals):
        # Gestion des many2one
        if vals.get('product_id', 0) < 0:
            vals['product_id'] = self.env['product.product'].browse(vals['product_id']).of_datastore_import().id

        # Gestion des many2many
        if vals.get('product_ids') and vals['product_ids'][0][2]:
            res = []
            product_ids = vals['product_ids'][0][2]
            ds_products = self.env['product.product'].browse([pid for pid in product_ids if pid < 0])

            # On appelle of_datastore_import() ici plutôt que dans le for
            # pour éviter d'appeler trop souvent la base centralisée
            products = ds_products.of_datastore_import()
            ds_products_dict = {p.of_datastore_res_id: p.id for p in products}

            for pid in product_ids:
                if pid < 0:
                    pid = ds_products_dict[-pid % DATASTORE_IND]
                res.append(pid)
            vals['product_ids'] = [[6, 0, res]]

        return super(OfDatastoreProductReference, self).write(vals)


class OfProductKitLine(models.Model):
    _name = 'of.product.kit.line'
    _inherit = ['of.product.kit.line', 'of.datastore.product.reference']

    @api.multi
    def _of_read_datastore(self, fields_to_read, create_mode=False):
        u"""
        Lit les données des kits dans leur base fournisseur.
        @param ids: id modifié des produits, en valeur négative
        """
        supplier_obj = self.env['of.datastore.supplier']
        brand_obj = self.env['of.product.brand']
        product_obj = self.env['product.product']
        res = []

        # Kits par fournisseur
        datastore_kit_ids = {}
        for full_id in self._ids:
            supplier_id = -full_id / DATASTORE_IND
            datastore_kit_ids.setdefault(supplier_id, []).append((-full_id) % DATASTORE_IND)

        for supplier in supplier_obj.browse(datastore_kit_ids):
            client = supplier.of_datastore_connect()
            ds_kit_obj = supplier.of_datastore_get_model(client, 'of.product.kit.line')

            # Données de la base fournisseur
            kits_data = supplier.of_datastore_read(ds_kit_obj, datastore_kit_ids[supplier.id], [])
            ds_product_ids = [kit['product_id'][0] for kit in kits_data]

            # Détection des composants du kit déjà importés
            # Attention de bien détecter les articles archivés (pourrait sinon provoquer des erreurs lors de l'import)
            products = product_obj.with_context(active_test=False).search(
                [('brand_id', 'in', supplier.brand_ids.ids),
                 ('of_datastore_res_id', 'in', ds_product_ids)])

            product_match = {product.of_datastore_res_id: product.id for product in products}
            product_names = dict(products.name_get())

            # Affectation des ids des champs relationnels
            supplier_value = supplier.id * DATASTORE_IND
            match_dicts = {}
            for kit in kits_data:
                # Articles
                product_id, product_name = kit['product_id']
                if product_id in product_match:
                    # Composant déjà importé
                    product_id = product_match[product_id]
                    product_name = product_names[product_id]
                else:
                    # Composant virtuel
                    product_id = -(product_id + supplier_value)
                kit['product_id'] = (product_id, product_name)
                kit['id'] = -(kit['id'] + supplier_value)

                # Unités de mesure
                uom_id, uom_name = kit['product_uom_id']
                uom_id = brand_obj.datastore_match(
                    client, 'product.uom', uom_id, uom_name, False, match_dicts, create=create_mode).id
                kit['product_uom_id'] = (uom_id, uom_name)
            res += kits_data
        return res

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        lines = self.filtered(lambda o: o.id > 0)
        ds_lines = self - lines

        # kits sur la base courante
        res = super(OfProductKitLine, self).read(fields, load=load)

        if ds_lines:
            res += ds_lines._of_read_datastore(fields)
        return res


class SaleOrderLine(models.Model):
    _name = 'sale.order.line'
    _inherit = ['sale.order.line', 'of.datastore.product.reference']

    of_brand_id = fields.Many2one(
        'of.product.brand', string="Filtre de marque",
        help=u"Ce champ permet de restreindre les articles proposés à une seule marque.\n"
             u"Renseigner ce champ permet aussi la recherche dans le tarif centralisé.\n"
             u"Utilisation équivalente au code m:XXX dans la recherche d'article, où XXX est le code de la marque")

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        if self.product_id and self.of_brand_id and self.product_id.brand_id != self.of_brand_id:
            self.of_brand_id = False
        return super(SaleOrderLine, self).product_id_change()

    @api.multi
    @api.onchange('of_brand_id')
    def _onchange_of_brand_id(self):
        if self.product_id and self.of_brand_id and self.product_id.brand_id != self.of_brand_id:
            self.product_id = False


class SaleOrderLineComp(models.Model):
    _name = 'of.saleorder.kit.line'
    _inherit = ['of.saleorder.kit.line', 'of.datastore.product.reference']


class AccountInvoiceLine(models.Model):
    _name = 'account.invoice.line'
    _inherit = ['account.invoice.line', 'of.datastore.product.reference']


class AccountInvoiceLineComp(models.Model):
    _name = 'of.invoice.kit.line'
    _inherit = ['of.invoice.kit.line', 'of.datastore.product.reference']


class PurchaseOrderLine(models.Model):
    _name = 'purchase.order.line'
    _inherit = ['purchase.order.line', 'of.datastore.product.reference']

    @api.onchange('product_qty', 'product_uom')
    def _onchange_quantity(self):
        res = super(PurchaseOrderLine, self)._onchange_quantity()
        if self.product_id.id < 0:
            self.price_unit = self.product_id.of_seller_price
            if self.product_uom != self.product_id.uom_id:
                self.price_unit = self.product_id.uom_id._compute_price(self.price_unit, self.product_uom)
        return res


class StockInventoryLine(models.Model):
    _name = 'stock.inventory.line'
    _inherit = ['stock.inventory.line', 'of.datastore.product.reference']


class StockMove(models.Model):
    _name = 'stock.move'
    _inherit = ['stock.move', 'of.datastore.product.reference']


class OFParcInstalle(models.Model):
    _name = 'of.parc.installe'
    _inherit = ['of.parc.installe', 'of.datastore.product.reference']
