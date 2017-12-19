# -*- coding: utf-8 -*-

from odoo import fields, models, api

"""
Ce fichier assure le passage de l'ancien système de kits au nouveau.
Il pourra être supprimé à l'issue de l'installation de ce module sur toutes les bases OpenFire

 - Désinstaller of_sale_kit sur toutes les bases
 - Supprimer le module of_sale_kit du dépôt
 - Supprimer l'appel aux fonctions ci-dessous dans data/of_kit_data.xml
 - Supprimer l'appel de ce fichier dans models/_init_.py
 - Supprimer ce fichier
"""

class OFKitInit(models.AbstractModel):
    _name = 'of.kit.init'

    def _init_kits_product(self):
        """
prend tous les kits de mrp et copie leurs composants de premier niveau en tant que composants de leur product_tmpl_id
-> pas besoin de créer d'article 
        """
        mrp_obj = self.env.get('mrp.bom')
        if not mrp_obj:
            # Le module mrp n'a pas été installé, donc pas de migration à effectuer
            return
        old_kits = self.search([('type', '=', 'phantom')])
        kit_line_obj = self.env['of.product.kit.line']
        for kit in old_kits:
            for line in kit.bom_line_ids:
                line_vals = {
                    'product_id': line.product_id.id,
                    'product_qty': line.product_qty,
                    'product_uom_id': line.product_uom_id.id,
                    'sequence': line.sequence,
                    'kit_id': kit.product_tmpl_id.id,
                }
                kit_line_obj.create(line_vals)
            kit_vals = {
                'of_is_kit': True,
                'of_pricing': kit.product_tmpl_id.pricing,
            }
            kit.product_tmpl_id.write(kit_vals)

    @api.model
    def _init_kits_sale_order(self):
        """
crée des kits pour chaque ligne de commande qui est un kit
prend tous les composants de la ligne et en créé des copies rattachées aux nouveaux kits créés
        """
        if 'sale.order.line.comp' not in self.env:
            # Le module of_sale_kit n'est pas installé, donc pas de migration à effectuer
            return
        orders = self.with_context({'active_test': False}).search([])
        new_saleorder_kit_obj = self.env['of.saleorder.kit']
        new_saleorder_kit_line_obj = self.env['of.saleorder.kit.line']
        for order in orders:
            for line in order.order_line:
                if line.child_ids != []:
                    line_vals = {
                        'of_is_kit': True,
                        'of_pricing': line.pricing,
                    }
                    line.write(line_vals)
                    kit_vals = {
                        'order_line_id': line.id,
                        'name': line.name,
                        'of_pricing': line.pricing
                    }
                    new_saleorder_kit = new_saleorder_kit_obj.create(kit_vals)
                    for comp in line.child_ids:
                        new_comp_vals = {
                            'kit_id': new_saleorder_kit.id,
                            'name': comp.name,
                            'default_code': comp.default_code,
                            'product_id': comp.product_id.id,
                            'product_uom_id': comp.product_uom.id,
                            'price_unit': comp.price_unit,
                            'cost_unit': comp.cost_unit,
                            'qty_per_kit': comp.qty_per_line,
                            'customer_lead': comp.customer_lead,
                            'qty_delivered': comp.qty_delivered,
                        }
                        new_saleorder_kit_line = new_saleorder_kit_line_obj.create(new_comp_vals)
                        for proc in comp.procurement_ids:
                            proc.of_sale_comp_id = new_saleorder_kit_line.id

    @api.model
    def _init_kits_invoice(self):
        """
crée des kits pour chaque ligne de facture qui est un kit
prend tous les composants de la ligne et en créé des copies rattachées aux nouveaux kits créés
        """
        if 'account.invoice.line.comp' not in self.env:
            # Le module of_sale_kit n'est pas installé, donc pas de migration à effectuer
            return
        invoices = self.search([])
        new_invoice_kit_obj = self.env['of.invoice.kit']
        new_invoice_kit_line_obj = self.env['of.invoice.kit.line']
        for invoice in invoices:
            for line in invoice.invoice_line_ids:
                if line.child_ids != []:
                    line_vals = {
                        'of_is_kit': True,
                        'of_pricing': line.pricing,
                    }
                    line.write(line_vals)
                    kit_vals = {
                        'invoice_line_id': line.id,
                        'name': line.name,
                        'of_pricing': line.pricing
                    }
                    new_invoice_kit = new_invoice_kit_obj.create(kit_vals)
                    for comp in line.child_ids:
                        new_comp_vals = {
                            'kit_id': new_invoice_kit.id,
                            'name': comp.name,
                            'default_code': comp.default_code,
                            'product_id': comp.product_id.id,
                            'product_uom_id': comp.uom_id.id,
                            'price_unit': comp.price_unit,
                            'cost_unit': comp.cost_unit,
                            'qty_per_kit': comp.qty_per_line,
                        }
                        new_invoice_kit_line_obj.create(new_comp_vals)

    @api.model
    def _init_new_kits(self):
        self._init_kits_product()
        self._init_kits_sale_order()
        self._init_kits_invoice()
