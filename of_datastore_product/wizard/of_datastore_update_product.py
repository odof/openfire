# -*- coding: utf-8 -*-

from osv import fields, osv
from tools.safe_eval import safe_eval
from addons.of_datastore_product.of_datastore_product import DATASTORE_IND
from openerp import SUPERUSER_ID
import time

class of_datastore_update_product(osv.TransientModel):
    _name = "of.datastore.update.product"
    _description = u"Importer / Mettre à jour les produits"


    def _get_ds_supplier_id(self, cr, uid, ids, name, arg, context=None):
        supplier_id = False
        if context:
            active_model = context.get('active_model')
            if active_model == 'of.datastore.supplier':
                supplier_id = context['active_ids'][0]
            elif active_model == 'product.product':
                product = self.pool[active_model].browse(cr, uid, context['active_ids'][0])
                supplier = product.datastore_supplier_id
                if supplier:
                    supplier_id = supplier.id
        return dict.fromkeys(ids,supplier_id)

    _columns = {
        'name'          : fields.boolean("Nom"),
        'code'          : fields.boolean(u"Référence"),
        'tarif'         : fields.boolean("Tarif", help=u"Mise à jour du prix d'achat et répercussion sur le prix de vente selon les règles définies dans le paramétrage"),
        'uom'           : fields.boolean("Unités de mesure", help=u"Mise à jour des unités de mesure utilisées pour les produits.\nLes unités manquantes seront créées au besoin"),
        'cg'            : fields.boolean("Conditions d'achat"),
        'categ'         : fields.boolean(u"Catégories de produits"),
        'kit'           : fields.boolean("Kits", help="Met à jour la composition des kits"),
        'act'           : fields.boolean("Produit inactif", help=u"Désactive les produits retirés par votre fournisseur"),
        'remember'      : fields.boolean(u"Se souvenir de mes préférences",
                                         help=u"Si cette case est cochée, vos préférences seront conservées pour votre prochaine mise à jour avec ce fournisseur"),
        'ds_supplier_id': fields.function(_get_ds_supplier_id, type="many2one", relation='of.datastore.supplier', string='Fournisseur'),
        'note'          : fields.text("Notes"),
        'is_update'     : fields.boolean(u'Afficher les options de mise à jour')
    }
    def _get_default_is_update(self, cr, uid, context):
        active_ids = context and context.get('active_ids') or []
        update_ids = [active_id for active_id in active_ids if active_id > 0]
        return bool(update_ids)
    _defaults = {
        'name' : True,
        'code' : True,
        'tarif': True,
        'cg'   : True,
        'act'  : True,
        'uom'  : True,
        'kit'  : True,
        'is_update': _get_default_is_update,
    }

    def default_get(self, cr, uid, fields_list, context=None):
        """
        Récupère les préférences enregitrées pour le fournisseur
        """
        defaults = super(of_datastore_update_product,self).default_get(cr, uid, fields_list, context=context)
        model = context and context.get('active_model')
        ds_supplier_id = False
        if model == 'of.datastore.supplier':
            ds_supplier_id = context['active_ids'][0]
        elif model == 'product.product':
            product_obj = self.pool['product.product']
            for product in product_obj.browse(cr, uid, context['active_ids'], context=context):
                if product.datastore_supplier_id:
                    ds_supplier_id = product.datastore_supplier_id.id
                    break
        if ds_supplier_id:
            defaults['ds_supplier_id'] = ds_supplier_id

            # code repris et modifie de default_get pour integrer la condition sur le fournisseur
            ir_values_obj = self.pool['ir.values']

            res = ir_values_obj.get(cr, uid, 'default', "supplier_%s"%ds_supplier_id, [self._name])
            for _, field, field_value in res:
                if field in fields_list:
                    fld_def = (field in self._columns) and self._columns[field] or self._inherit_fields[field][2]
                    if fld_def._type in ('many2one', 'one2one'):
                        obj = self.pool.get(fld_def._obj)
                        if not obj.search(cr, uid, [('id', '=', field_value or False)]):
                            continue
                    if fld_def._type in ('many2many'):
                        obj = self.pool.get(fld_def._obj)
                        field_value2 = []
                        for i in range(len(field_value)):
                            if not obj.search(cr, uid, [('id', '=',
                                field_value[i])]):
                                continue
                            field_value2.append(field_value[i])
                        field_value = field_value2
                    if fld_def._type in ('one2many'):
                        obj = self.pool.get(fld_def._obj)
                        field_value2 = []
                        for i in range(len(field_value)):
                            field_value2.append({})
                            for field2 in field_value[i]:
                                if field2 in obj._columns.keys() and obj._columns[field2]._type in ('many2one', 'one2one'):
                                    obj2 = self.pool.get(obj._columns[field2]._obj)
                                    if not obj2.search(cr, uid,
                                            [('id', '=', field_value[i][field2])]):
                                        continue
                                elif field2 in obj._inherit_fields.keys() and obj._inherit_fields[field2][2]._type in ('many2one', 'one2one'):
                                    obj2 = self.pool.get(obj._inherit_fields[field2][2]._obj)
                                    if not obj2.search(cr, uid,
                                            [('id', '=', field_value[i][field2])]):
                                        continue
                                # TODO add test for many2many and one2many
                                field_value2[i][field2] = field_value[i][field2]
                        field_value = field_value2
                    defaults[field] = field_value

        return defaults

    def _update_supplier_products(self, cr, uid, supplier, client, products, wizard_data, context):
        """
        Met a jour les produits products depuis la base fournisseur supplier
        @param supplier: browse_record of_datastore_supplier
        @param products: browse_record_list product.product
        @param wizard_data: dictionnaire des valeurs des champs du wizard
        """
        product_obj = self.pool['product.product']
        supplier_obj = self.pool['of.datastore.supplier']
        kit_rel_obj = self.pool['of.kit.relation']
        uom_obj = self.pool['product.uom']
        change_product_uom_categ_obj = self.pool['stock.change.product.uom.categ']

        supplier_value = supplier.id * DATASTORE_IND
        ds_product_obj = client.model('product.product')
        no_match = wizard_data['act'] and [product.id for product in products if not product.datastore_product_id]
        id_match = {product.datastore_product_id: product for product in products if product.datastore_product_id}
        margin_prec = product_obj._columns['price_margin'].digits[1]

        match_dicts = {}

        ds_product_ids = ds_product_obj.search([('id', 'in', id_match.keys())], context={'active_test':False})
        for ds_product in ds_product_ids and ds_product_obj.browse(ds_product_ids):
            product = id_match.pop(ds_product.id)
            product_data = {}

            # Mise a jour du libelle du produit
            if wizard_data['name'] and product.name != ds_product.name:
                product_data['name'] = ds_product.name

            # Mise a jour du code produit
            if wizard_data['code'] and product.default_code != ds_product.default_code:
                product_data['default_code'] = ds_product.default_code

            # Mise a jour de la categorie du produit
            ds_categ_id = ds_product.categ_id.id
            if wizard_data['categ']:
                categ_id = supplier_obj.get_matching_categ(cr, uid, supplier.id, client, [ds_categ_id], match_dicts=match_dicts, context=context)[ds_categ_id]
                if categ_id != product.categ_id.id:
                    product_data['categ_id'] = categ_id

            # Mise a jour du tarif
            if wizard_data['tarif']:

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

    def update_products(self, cr, uid, ids, context=None):
        if not context:
            return False
        supplier_obj = self.pool['of.datastore.supplier']
        active_model = context.get('active_model')
        active_ids = context.get('active_ids')
#        fields_available = ['pa','pv','cg','coeff','categ','act']

        wizard_id = ids[0]
        wizard_data = self.read(cr, uid, wizard_id, [], context=context)

        notes = [""]
        notes_warning = []

        # Preparation de la liste de produits par fournisseur
        datastore_products = {}
        model_obj = self.pool[active_model]
        if active_model == 'of.datastore.supplier':
            suppliers = model_obj.browse(cr, uid, active_ids, context=dict(context, active_test=False))
            datastore_products = {supplier: supplier.product_ids for supplier in suppliers}
        elif active_model == 'product.product':
            to_create = [product_id for product_id in active_ids if product_id<0]
            if to_create:
                model_obj.datastore_import(cr, uid, to_create, context)
                notes.append(u"Produits créés : %s" % (len(to_create)))

            to_update = [product_id for product_id in active_ids if product_id>0]
            for product in model_obj.browse(cr, uid, to_update):
                datastore_products.setdefault(product.datastore_supplier_id or False,[]).append(product)

            # Produits sans base fournisseur
            products = datastore_products.pop(False,[])
            if products:
                notes_warning = ["",u"Produits sans base fournisseur associée :"]
                for product in products:
                    notes_warning.append(" - "+product.partner_ref)

        # Recherche des valeurs a mettre a jour
        updt_cnt = 0
        for supplier,products in datastore_products.iteritems():
            client_dict = supplier.connect()
            try:
                self._update_supplier_products(cr, uid, supplier, client_dict[supplier.id], products, wizard_data, context)
            finally:
                supplier_obj.free_connection(client_dict)
            updt_cnt += len(products)
        if updt_cnt:
            notes.append(u"Produits mis à jour : %s" % (updt_cnt))

        # Enregistrement des choix
        if wizard_data['remember']:
            value_obj = self.pool['ir.values']
            for supplier in datastore_products:
                for field,value in wizard_data.iteritems():
                    if field in ('remember','ds_supplier_id','note'):
                        continue
                    value_obj.set_default(cr, SUPERUSER_ID, 'of.datastore.update.product', field, value,
                                          for_all_users=True, company_id=False, condition="supplier_%s"%supplier.id)

        notes[0] = u"Mise à jour des produits terminée à %s" % (time.strftime('%Hh%M:%S'),)
        note = "\n".join(notes + notes_warning)
        self.write(cr, uid, wizard_id, {'note':note}, context=context)
        return True
of_datastore_update_product()
