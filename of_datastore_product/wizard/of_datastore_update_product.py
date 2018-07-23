# -*- coding: utf-8 -*-

from odoo import models, fields, api
from addons.of_datastore_product.of_datastore_product import DATASTORE_IND
import time
from reportlab.lib.randomtext import objects

class OfDatastoreUpdateProduct(models.TransientModel):
    _name = "of.datastore.update.product"
    _description = u"Importer / Mettre à jour les articles"

    u_name = fields.Boolean(string="Nom", default=True)
    u_code = fields.Boolean(string=u"Référence", default=True)
    u_tarif = fields.Boolean(string="Tarif", default=True,
                             help=u"Mise à jour du prix d'achat et répercussion sur le prix de vente selon les règles définies dans le paramétrage")
    u_uom = fields.Boolean(string=u"Unités de mesure", default=True,
                           help=u"Mise à jour des unités de mesure utilisées pour les produits.\nLes unités manquantes seront créées au besoin")
    u_cg = fields.Boolean(string="Conditions d'achat", default=True)
    u_categ = fields.Boolean(string=u"Catégories de produits")
    u_kit = fields.Boolean(string="Kits", default=True, help="Met à jour la composition des kits")
    u_active = fields.Boolean(string="Produit inactif", default=True,
                              help=u"Désactive les produits retirés par votre fournisseur")
    remember = fields.Boolean(string=u"Se souvenir de mes préférences",
                              help=u"Si cette case est cochée, vos préférences seront conservées pour votre prochaine mise à jour avec ce fournisseur")
    brand_ids = fields.One2many('of.product.brand', compute='_compute_brand_ids', string='Marques')
    note = fields.Text("Notes")
    is_update = fields.Boolean(u'Afficher les options de mise à jour', default=lambda self: self._default_is_update())

    @api.depends()
    def _compute_brand_ids(self):
        for wizard in self:
            brands = False
            model = self._context.get('active_model')
            if model:
                objects = self.env[model].browse(self._context['active_ids'])
                if model == 'of.product.brand':
                    brands = objects
                elif model in ('product.product', 'product.template'):
                    brands = objects.mapped('brand_id')
            wizard.brand_ids = brands

    def _default_is_update(self):
        active_ids = self._context.get('active_ids') or [0]
        return max(active_ids) > 0

    @api.model
    def default_get(self, fields_list):
        """
        Récupère les préférences enregitrées pour le fournisseur
        """
        defaults = super(OfDatastoreUpdateProduct, self).default_get(fields_list)
        model = self._context.get('active_model')
        if not model:
            return defaults
        ds_supplier_id = False
        objects = self.env['model'].browse(self._context['active_ids'])
        if model == 'of.product.brand':
            for brand in objects:
                if brand.datastore_supplier_id:
                    ds_supplier_id = brand.datastore_supplier_id.id
                    break
        elif model == 'product.product':
            for product in objects:
                if product.of_datastore_supplier_id:
                    ds_supplier_id = product.of_datastore_supplier_id.id
                    break
        if ds_supplier_id:
            defaults['ds_supplier_id'] = ds_supplier_id
            # code repris et modifié de default_get pour intégrer la condition sur le fournisseur
            ir_values_dict = self.env['ir.values'].get_defaults_dict(self._name, "supplier_%s" % ds_supplier_id)
            for name in fields_list:
                if name in ir_values_dict:
                    defaults[name] = ir_values_dict[name]
                    continue
        return defaults

    def _update_supplier_products(self, supplier, products):
        """
        Met a jour les produits products depuis la base fournisseur supplier
        @param supplier: browse_record of_datastore_supplier
        @param products: browse_record_list product.product
        """
        product_obj = self.env['product.product']
        supplier_obj = self.env['of.datastore.supplier']
        kit_rel_obj = self.env['of.kit.relation']
        uom_obj = self.env['product.uom']
        change_product_uom_categ_obj = self.env['stock.change.product.uom.categ']

        supplier_value = supplier.id * DATASTORE_IND
        client = supplier.of_datastore_connect()
        ds_product_obj = supplier.of_datastore_get_model(client, 'product.product')
        ds_seller_obj = supplier.of_datastore_get_model(client, 'product.supplierinfo')
        ds_kit_line_obj = supplier.of_datastore_get_model(client, 'of.kit.relation')
        no_match = self.act and [product.id for product in products if not product.datastore_product_id]
        id_match = {product.datastore_product_id: product for product in products if product.datastore_product_id}
        margin_prec = product_obj._columns['price_margin'].digits[1]

        match_dicts = {}

#         ds_product_ids = supplier.with_context(active_test=True).of_datastore_search(ds_product_obj, [('id', 'in', id_match.keys())])
#         fields_to_read = (
#             'name',
#             'default_code',
#             'categ_id',
#             'date_tarif', 'price_extra', 'ecopart_ht', 'standard_price', 'price_remise', 'list_pvht',
#             'uom_id', 'uos_id', 'uom_po_id',
#             'seller_ids',
#             'kit', 'kit_lines',
#             'active'
#         )
        fields_to_read = product_obj.of_datastore_get_import_fields()
        for ds_product in product_obj.browse(ds_product_ids).read()
        
        
        
        for ds_product in ds_product_ids and ds_product_obj.read(ds_product_ids, fields_to_read):
            product = id_match.pop(ds_product['id'])
            product_data = {}

            # Mise a jour du libelle du produit
            if self.u_name and product.name != ds_product['name']:
                product_data['name'] = ds_product['name']

            # Mise a jour du code produit
            if self.u_code and product.default_code != ds_product['default_code']:
                product_data['default_code'] = ds_product['default_code']

            # Mise a jour de la categorie du produit
            ds_categ_id = ds_product['categ_id'][0]
            if self.u_categ:
                categ_id = supplier_obj.get_matching_categ(cr, uid, supplier.id, client, [ds_categ_id], match_dicts=match_dicts, context=context)[ds_categ_id]
                if categ_id != product.categ_id.id:
                    product_data['categ_id'] = categ_id

            # Mise a jour du tarif
            if wizard_data['tarif']:

                # Mise à jour de la date du tarif
                date_tarif = ds_product['date_tarif']
                if date_tarif and date_tarif != product.date_tarif:
                    product_data['date_tarif'] = date_tarif

                # Mise à jour des frais extra
                price_extra = ds_product['price_extra']
                if price_extra != product.price_extra:
                    product_data['price_extra'] = price_extra

                # Mise à jour de l'eco-participation
                ecopart_ht = ds_product['ecopart_ht']
                if ecopart_ht != product.ecopart_ht:
                    product_data['ecopart_ht'] = ecopart_ht

                # Mise à jour du prix d'achat
                standard_price = ds_product['standard_price']
                price_remise = ds_product['price_remise']
                eval_dict = {
                    'rc'   : price_remise, # Remise conseillee
                    'ra'   : product.price_remise,    # Remise actuelle
                    'cumul': supplier_obj.compute_remise,
                }
                remise_eval = supplier_obj.get_matching_remise(cr, uid, supplier.id, client, [ds_categ_id], match_dicts=match_dicts, field='remise', context=context)[ds_categ_id]
                remise = safe_eval(remise_eval, eval_dict)
                if remise != price_remise:
                    if remise >= 100:
                        standard_price = 0.0
                    else:
                        standard_price = round(standard_price * (100-remise)/(100.0-price_remise), 2)

                if standard_price != product.standard_price:
                    product_data['list_price'] = product_data['standard_price'] = standard_price
    
                # Mise a jour du prix de vente TTC
                eval_dict.update({
                    'r'  : remise,
                    'pv' : price_extra + standard_price * 100 / (100.0 - remise) if remise<100 else ds_product['list_pvht'],
                    'tf' : price_extra,
                })
                price_eval = supplier_obj.get_matching_remise(cr, uid, supplier.id, client, [ds_categ_id], match_dicts=match_dicts, field='price_ttc', context=context)[ds_categ_id]
                list_pvht = safe_eval(price_eval, eval_dict)
                if list_pvht != product.list_pvht:
                    product_data['list_pvht'] = list_pvht

                # Mise a jour de la remise
                price_margin = standard_price and round((list_pvht - price_extra) / standard_price, margin_prec) or 1
                if price_margin != product.price_margin:
                    product_data['price_margin'] = price_margin

            # Mise a jour des unites de mesure
            if wizard_data['uom']:
                # Mise a jour de la categorie des unites de mesure
                new_uom_ids = []
                for uom in (ds_product['uom_id'], ds_product['uos_id'], ds_product['uom_po_id']):
                    new_uom_ids.append(uom and supplier_obj.datastore_match(cr, uid, supplier.id, client, 'product.uom', uom[0], match_dicts, create=True, context=context) or False)

                new_uom = uom_obj.browse(cr, uid, new_uom_ids[0])
                if product.uom_id.category_id != new_uom.category_id:
                    # La categorie d'udm a change
                    #   utilisation du code de of_sales/wizard/stock_change_product_uom_categ
                    fields = change_product_uom_categ_obj._columns.keys()
                    wizard_context = {
                        'active_id': product.id,
                    }
                    values = change_product_uom_categ_obj.default_get(cr, uid, fields, context=wizard_context)

                    # Preparation du browse_record_list pour limiter le nombre de read
                    uom_ids = [line[2]['old_uom_id'] for line in values['line_ids']]
                    uoms = uom_obj.browse(cr, uid, uom_ids, context=context)
                    uoms = {uom.id: uom for uom in uoms}

                    # Calcul des correspondances des udm
                    for line in values['line_ids']:
                        vals = line[2]
                        uom_id = vals['old_uom_id']
                        uom = uoms[uom_id]

                        # Code de matching copie depuis of_datastore_supplier.datastore_match
                        uom_ids = uom_obj.search(cr, uid, [('factor','=',uom.factor),
                                                           ('uom_type','=',uom.uom_type),
                                                           ('category_id','=',new_uom.category_id.id)], context=context)
            
                        if uom_ids:
                            if len(uom_ids) > 1:
                                # Ajout d'un filtre sur le nom pour préciser la recherche
                                uom_ids = uom_obj.search(cr, uid, [('id','in',uom_ids),('name','=ilike',uom.name)]) or uom_ids
                            if len(uom_ids) > 1:
                                # Ajout d'un filtre sur la précision de l'arrondi pour préciser la recherche
                                uom_ids = uom_obj.search(cr, uid, [('id','in',uom_ids),('rounding','=',uom.rounding)]) or uom_ids
                            uom_id = uom_ids[0]
                        else:
                            # Creation d'une nouvelle udm
                            uom_data = {
                                'name'       : uom.name,
                                'uom_type'   : uom.uom_type,
                                'factor'     : uom.factor,
                                'category_id': new_uom.category_id.id,
                                'rounding'   : uom.rounding,
                            }
                            uom_id = uom_obj.create(cr, uid, uom_data, context=context)
                        vals['new_uom_id'] = uom_id
                    # Creation et lancement de l'action du wizard
                    wizard_id = change_product_uom_categ_obj.create(cr, uid, values, context=context)
                    change_product_uom_categ_obj.change_product_udm_categ(cr, uid, [wizard_id], context=context)

                # Mise a jour des unites de mesure
                if product.uom_id.id != new_uom_ids[0]:
                    product_data['uom_id'] = new_uom_ids[0]
                if product.uos_id.id != new_uom_ids[1]:
                    product_data['uos_id'] = new_uom_ids[1]
                if product.uom_po_id.id != new_uom_ids[2]:
                    product_data['uom_po_id'] = new_uom_ids[2]

            # Mise a jour de product_supplierinfo
            if wizard_data['cg']:
                for seller in product.seller_ids:
                    if seller.name == supplier.partner_id:
                        break
                else:
                    seller = False
                ds_seller_id = ds_product['seller_ids'] and ds_product['seller_ids'][0]
                ds_seller = ds_seller_obj.read(ds_seller_id, ['min_qty', 'delay'])

                if seller:
                    seller_data = {}
                    for field in ('min_qty', 'delay'):
                        if getattr(seller, field) != ds_seller[field]:
                            seller_data[field] = ds_seller[field]
                    if seller_data:
                        product_data['seller_ids'] = [(1,seller.id,seller_data)]
                else:
                    # Ne devrait pas arriver ...
                    product_data['seller_id'] = [(0,0,{
                        'name'       : supplier.partner_id.id,
                        'product_uom': product.uom_id.id,
                        'min_qty'    : ds_seller['min_qty'],
                        'delay'      : ds_seller['delay'],
                    })]

            if wizard_data['kit']:
                if ds_product['kit']:
                    if not product.kit:
                        product_data['kit'] = True
                    lines_changed = len(ds_product['kit_lines']) != len(product.kit_lines)
                    if not lines_changed:
                        ind = 0
                        for ds_line in ds_kit_line_obj.read(ds_product['kit_lines'], ('qty', 'sequence', 'product_id')):
                            line = product.kit_lines[ind]
                            if ds_line['qty'] != line.qty or ds_line['sequence'] != line.sequence or ds_line['product_id'][0] != line.product_id.datastore_product_id:
                                lines_changed = True
                                break
                            ind += 1
                    if lines_changed:
                        line_ids = [-(ds_line_id + supplier_value) for ds_line_id in ds_product['kit_lines']]
                        product_data['kit_lines'] = [(5, )]+[(0, 0, kit_rel_obj.copy_data(cr, uid, line_id, context=context)) for line_id in line_ids]

                elif product.kit:
                    product_data['kit'] = False
                    product_data['kit_lines'] = [(5, )]

            # Mise a jour produits actifs/inactifs
            if wizard_data['act']:
                if ds_product['active']:
                    if product.state == 'end':
                        # On ne reactive que les produits notes 'en fin de vie' pour eviter de reactiver un produit desactive manuellement
                        product_data['state'] = 'sellable' # Produit disponible
                        if not product.active:
                            product_data['active'] = True
                else:
                    if product.active:
                        if product.virtual_available != 0:
                            product_data['active'] = False
                        if product.state != 'end':
                            product_data['state'] = 'end'

            if product_data:
                product.write(product_data)
        if wizard_data['act']:
            no_match += [product.id for product in id_match.values()]
            # On ne desactive pas les produits encore presents en stock
            product_ids = product_obj.search(cr, uid, [('id','in',no_match),('virtual_available','>',0)], context=context)
            product_obj.write(cr, uid, product_ids, {'datastore_product_id':False, 'state':'end'}, context=context)

            product_ids = [product_id for product_id in no_match if product_id not in product_ids]
            product_obj.write(cr, uid, product_ids, {'active':False, 'datastore_product_id':False}, context=context)
        return True









    def _update_supplier_products2(self, supplier, products):
        """
        Met a jour les produits products depuis la base fournisseur supplier
        @param supplier: browse_record of_datastore_supplier
        @param products: browse_record_list product.product
        @param wizard_data: dictionnaire des valeurs des champs du wizard
        """
        product_obj = self.env['product.product']
        supplier_obj = self.env['of.datastore.supplier']
        kit_rel_obj = self.env['of.kit.relation']
        uom_obj = self.env['product.uom']
        change_product_uom_categ_obj = self.env['stock.change.product.uom.categ']

        supplier_value = supplier.id * DATASTORE_IND
        client = supplier.of_datastore_connect()
        ds_product_obj = supplier.of_datastore_get_model(client, 'product.product')
        no_match = self.act and [product.id for product in products if not product.datastore_product_id]
        id_match = {product.of_datastore_product_id: product for product in products if product.datastore_product_id}
        margin_prec = product_obj._columns['price_margin'].digits[1]

        match_dicts = {}

        ds_product_ids = ds_product_obj.with_context(active_test=False).search([('id', 'in', id_match.keys())])
        for ds_product in ds_product_obj.browse(ds_product_ids):
            product = id_match.pop(ds_product.id)
            product_data = {}

            # Mise a jour du libelle du produit
            if self.u_name and product.name != ds_product.name:
                product_data['name'] = ds_product.name

            # Mise a jour du code produit
            if self.u_code and product.default_code != ds_product.default_code:
                product_data['default_code'] = ds_product.default_code

            # Mise a jour de la categorie du produit
            ds_categ_id = ds_product.categ_id.id
            if self.u_categ:
                categ_id = supplier_obj.get_matching_categ(cr, uid, supplier.id, client, [ds_categ_id], match_dicts=match_dicts, context=context)[ds_categ_id]
                if categ_id != product.categ_id.id:
                    product_data['categ_id'] = categ_id

            # Mise a jour du tarif
            if self.u_tarif:

                # Mise à jour de la date du tarif
                date_tarif = ds_product.date_tarif
                if date_tarif and date_tarif != product.date_tarif:
                    product_data['date_tarif'] = date_tarif

                # Mise à jour des frais extra
                price_extra = ds_product.price_extra
                if price_extra != product.price_extra:
                    product_data['price_extra'] = price_extra

                # Mise à jour de l'eco-participation
                ecopart_ht = ds_product.ecopart_ht
                if ecopart_ht != product.ecopart_ht:
                    product_data['ecopart_ht'] = ecopart_ht

                # Mise à jour du prix d'achat
                standard_price = ds_product.standard_price
                price_remise = ds_product.price_remise
                eval_dict = {
                    'rc'   : price_remise, # Remise conseillee
                    'ra'   : product.price_remise,    # Remise actuelle
                    'cumul': supplier_obj.compute_remise,
                }
                remise_eval = supplier_obj.get_matching_remise(cr, uid, supplier.id, client, [ds_categ_id], match_dicts=match_dicts, field='remise', context=context)[ds_categ_id]
                remise = safe_eval(remise_eval, eval_dict)
                if remise != price_remise:
                    if remise >= 100:
                        standard_price = 0.0
                    else:
                        standard_price = round(standard_price * (100-remise)/(100.0-price_remise), 2)

                if standard_price != product.standard_price:
                    product_data['list_price'] = product_data['standard_price'] = standard_price
    
                # Mise a jour du prix de vente TTC
                eval_dict.update({
                    'r'  : remise,
                    'pv' : price_extra + standard_price * 100 / (100.0 - remise) if remise<100 else ds_product.list_pvht,
                    'tf' : price_extra,
                })
                price_eval = supplier_obj.get_matching_remise(cr, uid, supplier.id, client, [ds_categ_id], match_dicts=match_dicts, field='price_ttc', context=context)[ds_categ_id]
                list_pvht = safe_eval(price_eval, eval_dict)
                if list_pvht != product.list_pvht:
                    product_data['list_pvht'] = list_pvht

                # Mise a jour de la remise
                price_margin = standard_price and round((list_pvht - price_extra) / standard_price, margin_prec) or 1
                if price_margin != product.price_margin:
                    product_data['price_margin'] = price_margin

            # Mise a jour des unites de mesure
            if wizard_data['uom']:
                # Mise a jour de la categorie des unites de mesure
                new_uom_ids = []
                for uom in (ds_product.uom_id, ds_product.uos_id, ds_product.uom_po_id):
                    new_uom_ids.append(uom and supplier_obj.datastore_match(cr, uid, supplier.id, client, 'product.uom', uom.id, match_dicts, create=True, context=context) or False)

                new_uom = uom_obj.browse(cr, uid, new_uom_ids[0])
                if product.uom_id.category_id != new_uom.category_id:
                    # La categorie d'udm a change
                    #   utilisation du code de of_sales/wizard/stock_change_product_uom_categ
                    fields = change_product_uom_categ_obj._columns.keys()
                    wizard_context = {
                        'active_id': product.id,
                    }
                    values = change_product_uom_categ_obj.default_get(cr, uid, fields, context=wizard_context)

                    # Preparation du browse_record_list pour limiter le nombre de read
                    uom_ids = [line[2]['old_uom_id'] for line in values['line_ids']]
                    uoms = uom_obj.browse(cr, uid, uom_ids, context=context)
                    uoms = {uom.id: uom for uom in uoms}

                    # Calcul des correspondances des udm
                    for line in values['line_ids']:
                        vals = line[2]
                        uom_id = vals['old_uom_id']
                        uom = uoms[uom_id]

                        # Code de matching copie depuis of_datastore_supplier.datastore_match
                        uom_ids = uom_obj.search(cr, uid, [('factor','=',uom.factor),
                                                           ('uom_type','=',uom.uom_type),
                                                           ('category_id','=',new_uom.category_id.id)], context=context)
            
                        if uom_ids:
                            if len(uom_ids) > 1:
                                # Ajout d'un filtre sur le nom pour préciser la recherche
                                uom_ids = uom_obj.search(cr, uid, [('id','in',uom_ids),('name','=ilike',uom.name)]) or uom_ids
                            if len(uom_ids) > 1:
                                # Ajout d'un filtre sur la précision de l'arrondi pour préciser la recherche
                                uom_ids = uom_obj.search(cr, uid, [('id','in',uom_ids),('rounding','=',uom.rounding)]) or uom_ids
                            uom_id = uom_ids[0]
                        else:
                            # Creation d'une nouvelle udm
                            uom_data = {
                                'name'       : uom.name,
                                'uom_type'   : uom.uom_type,
                                'factor'     : uom.factor,
                                'category_id': new_uom.category_id.id,
                                'rounding'   : uom.rounding,
                            }
                            uom_id = uom_obj.create(cr, uid, uom_data, context=context)
                        vals['new_uom_id'] = uom_id
                    # Creation et lancement de l'action du wizard
                    wizard_id = change_product_uom_categ_obj.create(cr, uid, values, context=context)
                    change_product_uom_categ_obj.change_product_udm_categ(cr, uid, [wizard_id], context=context)

                # Mise a jour des unites de mesure
                if product.uom_id.id != new_uom_ids[0]:
                    product_data['uom_id'] = new_uom_ids[0]
                if product.uos_id.id != new_uom_ids[1]:
                    product_data['uos_id'] = new_uom_ids[1]
                if product.uom_po_id.id != new_uom_ids[2]:
                    product_data['uom_po_id'] = new_uom_ids[2]

            # Mise a jour de product_supplierinfo
            if wizard_data['cg']:
                for seller in product.seller_ids:
                    if seller.name == supplier.partner_id:
                        break
                else:
                    seller = False
                ds_seller = ds_product.seller_ids[0]

                if seller:
                    seller_data = {}
                    for field in ('min_qty', 'delay'):
                        if getattr(seller, field) != getattr(ds_seller, field):
                            seller_data[field] = getattr(ds_seller, field)
                    if seller_data:
                        product_data['seller_ids'] = [(1,seller.id,seller_data)]
                else:
                    # Ne devrait pas arriver ...
                    product_data['seller_id'] = [(0,0,{
                        'name'       : supplier.partner_id.id,
                        'product_uom': product.uom_id.id,
                        'min_qty'    : ds_seller.min_qty,
                        'delay'      : ds_seller.delay,
                    })]

            if wizard_data['kit']:
                if ds_product.kit:
                    if not product.kit:
                        product_data['kit'] = True
                    lines_changed = len(ds_product.kit_lines) != len(product.kit_lines)
                    if not lines_changed:
                        ind = 0
                        for ds_line in ds_product.kit_lines:
                            line = product.kit_lines[ind]
                            if ds_line.qty != line.qty or ds_line.sequence != line.sequence or ds_line.product_id.id != line.product_id.datastore_product_id:
                                lines_changed = True
                                break
                            ind += 1
                    if lines_changed:
                        line_ids = [-(ds_line.id + supplier_value) for ds_line in ds_product.kit_lines]
                        product_data['kit_lines'] = [(5,)]+[(0,0,kit_rel_obj.copy_data(cr, uid, line_id, context=context)) for line_id in line_ids]

                elif product.kit:
                    product_data['kit'] = False
                    product_data['kit_lines'] = [(5,)]

            # Mise a jour produits actifs/inactifs
            if wizard_data['act']:
                if ds_product.active:
                    if product.state == 'end':
                        # On ne reactive que les produits notes 'en fin de vie' pour eviter de reactiver un produit desactive manuellement
                        product_data['state'] = 'sellable' # Produit disponible
                        if not product.active:
                            product_data['active'] = True
                else:
                    if product.active:
                        if product.virtual_available != 0:
                            product_data['active'] = False
                        if product.state != 'end':
                            product_data['state'] = 'end'

            if product_data:
                product.write(product_data)
        if wizard_data['act']:
            no_match += [product.id for product in id_match.values()]
            # On ne desactive pas les produits encore presents en stock
            product_ids = product_obj.search(cr, uid, [('id','in',no_match),('virtual_available','>',0)], context=context)
            product_obj.write(cr, uid, product_ids, {'datastore_product_id':False, 'state':'end'}, context=context)

            product_ids = [product_id for product_id in no_match if product_id not in product_ids]
            product_obj.write(cr, uid, product_ids, {'active':False, 'datastore_product_id':False}, context=context)
        return True

    @api.multi
    def update_products(self):
        self.ensure_one()
        active_model = self._context.get('active_model')
        active_ids = self._context.get('active_ids')
        model_obj = self.env[active_model]
#        fields_available = ['pa','pv','cg','coeff','categ','act']

        notes = [""]
        notes_warning = []

        # Preparation de la liste de produits par fournisseur
        datastore_products = {}
        if active_model == 'of.product.brand':
            brands = model_obj.browse(active_ids)
            suppliers = brands.mapped('datastore_supplier_id')
            datastore_products = {supplier: supplier.product_ids for supplier in suppliers}
            
            for brand in brands:
                if brand.datastore_supplier_id not in datastore_products:
                    datastore_products[brand.datastore_supplier_id] = brand.product_ids
                else:
                    datastore_products[brand.datastore_supplier_id] += brand.product_ids
        elif active_model in ('product.product', 'product.template'):
            to_create = [product_id for product_id in active_ids if product_id < 0]
            if to_create:
                model_obj.browse(to_create).of_datastore_import()
                notes.append(u"Produits créés : %s" % (len(to_create)))

            to_update = [product_id for product_id in active_ids if product_id > 0]
            products = model_obj.browse(to_update)
            if active_model == 'product.template':
                products = products.mapped('product_variant_ids')
            for product in model_obj.browse(to_update):
                if product.datastore_supplier_id in datastore_products:
                    datastore_products[product.datastore_supplier_id] += product
                else:
                    datastore_products[product.datastore_supplier_id] = product

            # Produits sans base fournisseur
            products = datastore_products.pop(False,[])
            if products:
                notes_warning = ["",u"Produits sans base fournisseur associée :"]
                for product in products:
                    notes_warning.append(" - "+product.partner_ref)

        # Recherche des valeurs à mettre à jour
        updt_cnt = 0
        for supplier, products in datastore_products.iteritems():
            self._update_supplier_products(supplier, products)
            updt_cnt += len(products)
        if updt_cnt:
            notes.append(u"Produits mis à jour : %s" % (updt_cnt))

        # Enregistrement des choix
        if self.remember:
            value_obj = self.env['ir.values'].sudo()
            for field in self._fields:
                if field.startswith('u_'):
                    for supplier in datastore_products:
                        value_obj.set_default(self._name, field, self[field], for_all_users=True, company_id=False,
                                              condition='supplier_%s' % supplier.id)

        notes[0] = u"Mise à jour des produits terminée à %s" % (time.strftime('%Hh%M:%S'),)
        self.note = "\n".join(notes + notes_warning)
