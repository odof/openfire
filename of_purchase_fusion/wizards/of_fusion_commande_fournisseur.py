# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OfFusionCommandeFournisseur(models.TransientModel):
    _name = "of.fusion.commande.fournisseur"
    _description = u"Wizard de fusion pour les commandes d'un même fournisseur"

    texte = fields.Char('Information')
    affichage = fields.Boolean('aff')

    @api.onchange('affichage')
    def _onchange_affichage(self):
        if not self.affichage:
            purchase_order_obj = self.env['purchase.order']

            purchase_orders = purchase_order_obj.browse(self._context['active_ids'])
            if len(purchase_orders) <= 1:
                self.texte = u"Il faut sélectionner plusieurs commandes pour une fusion."
                self.affichage = True
                return

            filtered_orders = purchase_orders\
                .with_context(partner_id=purchase_orders[0].partner_id.id)\
                .filtered(lambda order: order.partner_id.id == order._context['partner_id'])
            if purchase_orders != filtered_orders:
                self.texte = u"Les commandes ont des fournisseurs différents."
                self.affichage = True
                return

            names = [order.name for order in purchase_orders]
            self.texte = "Vous allez fusionner les commandes " + ', '.join(names)\
                         + u".\n Êtes vous certains de vouloir continuer ?"

    @api.multi
    def button_merge_orders(self):
        procurement_order_obj = self.env['procurement.order']
        purchase_order_obj = self.env['purchase.order']
        stock_move_obj = self.env['stock.move']

        purchase_orders = purchase_order_obj.browse(self._context['active_ids'])
        procurement_orders = procurement_order_obj.search([('purchase_id', 'in', purchase_orders._ids)])

        # Fusion sur la première commande de la liste qui est généralement aussi la dernière créée
        fuse_on = purchase_orders[0]
        customer = fuse_on.customer_id
        project = fuse_on.of_project_id

        sale_orders = self.env['sale.order'].browse()
        for order in purchase_orders:
            if order.customer_id != customer:
                customer = False
            if order.of_project_id != project:
                project = False
            if order.order_line:
                order.order_line.filtered(lambda l: not l.of_customer_id).write(
                    {'of_customer_id': order.customer_id.id})
                order.order_line.write({'order_id': fuse_on.id, 'of_delivery_expected': order.delivery_expected})
            if order.sale_order_id:
                sale_orders += order.sale_order_id + order.of_sale_order_ids

        procurement_orders.write({'purchase_id': fuse_on.id})
        fuse_on.write(
            {'of_sale_order_ids': [(6, False, sale_orders.ids)],
             'of_fused': True,
             'customer_id': customer and customer.id,
             'of_project_id': project and project.id})
        # màj origin dans les BRs
        for picking in fuse_on.picking_ids:
            picking.origin = fuse_on.name

        delete_orders = purchase_orders - fuse_on
        for order in delete_orders:
            order.button_cancel()

            # On met à jour l'origine des mouvements de stock
            move_lines = stock_move_obj.search([('origin', '=', order.name)])
            move_lines.write({'origin': fuse_on.name})

        delete_orders.unlink()

        return self.env['of.popup.wizard'].popup_return(
            u'Toutes les commandes ont été fusionnées sur la commande ' + fuse_on.name + '.', 'Information')
