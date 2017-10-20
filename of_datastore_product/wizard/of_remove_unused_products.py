# -*- coding: utf-8 -*-

from osv import fields, osv
import time

class of_remove_unused_products(osv.TransientModel):
    _name = "of.remove.unused.products"

    _columns = {
        'partner_id' : fields.many2one('res.partner', 'Fournisseur', domain=[('supplier','=',True)],
                                       help="Si défini, seuls les produits de ce fournisseur seront affectés"),
        'product_ids': fields.many2many('product.product', 'remove_products_product', 'wizard_id', 'product_id', 'Produits', readonly=True),
    }

    def get_unused_products(self, cr, uid, ids, context=None):
        wizard = self.browse(cr, uid, ids[0], context=context)
        query = "SELECT p.id FROM product_product AS p "
        where_query = []
        if wizard.partner_id:
            where_query = ["p.product_tmpl_id IN (SELECT product_id FROM product_supplierinfo WHERE name=%s)"% wizard.partner_id.id]
        objects = (
        'account.invoice.line',
        'account.invoice.line.comp',
        'mrp.bom',
        'of.kit.relation',
        'of.planning.tache',
        'of.product.nomenclature.line',
        'purchase.order.line',
        'sale.order.line',
        'sale.order.line.comp',
        'stock.inventory.line',
        'stock.move',
        )

        # Important : ne pas retirer le DISTINCT (sur cas pratique, passage de 20 minutes a 1 seconde de calcul)
        where_query += ["p.id NOT IN (SELECT DISTINCT product_id FROM %s WHERE product_id IS NOT NULL)" % (self.pool[o]._table,)
                        for o in objects if self.pool.get(o)]

        # Cas particulier, on ne supprime pas de kit
        if self.pool.get('of.kit.relation'):
            where_query.append('NOT p.kit ')
        where_query = "WHERE " + " AND ".join(where_query)
        cr.execute(query + where_query)

        product_ids = [row[0] for row in cr.fetchall()]
        if product_ids:
            # Selection des produits en fonction des droits de l'utilisateur
            product_ids = self.pool['product.product'].search(cr, uid, [('id', 'in', product_ids)], context=context)
        return product_ids

    def remove_unused_products(self, cr, uid, ids, context=None):
        product_obj = self.pool['product.product']
        product_ids = self.get_unused_products(cr, uid, ids, context=context)
        # Sur de grosses bases la suppression de produits est tres longue
        # cr.split_for_in_conditions separera par defaut les ids en paquets de 1000
        # cr.commit permettra de ne pas perdre le travail effectue en cas de coupure
        for sub_ids in cr.split_for_in_conditions(product_ids):
            product_obj.unlink(cr, uid, sub_ids, context=context)
            cr.commit()
        return {'type': 'ir.actions.act_window_close'}

    def show_unused_products(self, cr, uid, ids, context=None):
        product_ids = self.get_unused_products(cr, uid, ids, context=context)
        self.write(cr, uid, ids, {'product_ids': [(6,0,product_ids)]})
        return True

of_remove_unused_products()


