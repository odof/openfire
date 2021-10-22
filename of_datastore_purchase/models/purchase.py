# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    of_datastore_purchase = fields.Boolean(string=u"Connecteur achat ?", compute='_compute_of_datastore_purchase')
    of_datastore_sent = fields.Boolean(string=u"CF envoyée via connecteur achat", copy=False)

    @api.multi
    def _compute_of_datastore_purchase(self):
        for order in self:
            if self.env['of.datastore.purchase'].search([('partner_id', '=', order.partner_id.id)]):
                order.of_datastore_purchase = True
            else:
                order.of_datastore_purchase = False

    @api.multi
    def button_datastore_send_order(self):
        self.ensure_one()

        # On vérifie que la commande n'a pas déjà été envoyée
        if self.of_datastore_sent:
            raise UserError(u"La commande a déjà été envoyée par le connecteur !")

        # On vérifie s'il existe un connecteur achat pour ce fournisseur
        datastore_purchase = self.env['of.datastore.purchase'].search([('partner_id', '=', self.partner_id.id)])
        if datastore_purchase:
            client = datastore_purchase.of_datastore_connect()
            if isinstance(client, basestring):
                raise UserError(u"Échec de la connexion au connecteur achat !")

            ds_partner_obj = datastore_purchase.of_datastore_get_model(client, 'res.partner')
            ds_sale_order_obj = datastore_purchase.of_datastore_get_model(client, 'sale.order')
            ds_sale_order_line_obj = datastore_purchase.of_datastore_get_model(client, 'sale.order.line')
            ds_warehouse_obj = datastore_purchase.of_datastore_get_model(client, 'stock.warehouse')
            ds_product_obj = datastore_purchase.of_datastore_get_model(client, 'product.product')
            ds_values_obj = datastore_purchase.of_datastore_get_model(client, 'ir.values')
            ds_fiscal_pos_tax_obj = datastore_purchase.of_datastore_get_model(client, 'account.fiscal.position.tax')

            # On récupère le client sur la base fournisseur
            partner_ids = datastore_purchase.of_datastore_search(
                ds_partner_obj, [('of_datastore_id', '=', datastore_purchase.datastore_id)])
            if partner_ids:
                partner_id = partner_ids[0]
            else:
                raise UserError(u"Identifiant inconnu chez le fournisseur !")

            # Si l'article divers n'a jamais été renseigné il renvoie une erreur.
            try:
                product_divers_id = datastore_purchase.of_datastore_func(
                    ds_values_obj, 'get_default', ['sale.config.settings', 'of_datastore_sale_misc_product_id'], [])
            except:
                raise UserError(u"Article divers non renseigné chez le fournisseur !")
            if not product_divers_id:
                raise UserError(u"Article divers non renseigné chez le fournisseur !")

            # Création de la commande de vente

            partner_invoice_ids = datastore_purchase.of_datastore_search(
                ds_partner_obj, [('parent_id', '=', partner_id), ('type', '=', 'invoice')],
                order='of_default_address DESC')
            if partner_invoice_ids:
                partner_invoice_id = partner_invoice_ids[0]
            else:
                partner_invoice_id = partner_id

            partner_shipping_ids = datastore_purchase.of_datastore_search(
                ds_partner_obj, [('parent_id', '=', partner_id), ('type', '=', 'delivery')],
                order='of_default_address DESC')
            if partner_shipping_ids:
                partner_shipping_id = partner_shipping_ids[0]
            else:
                partner_shipping_id = partner_id

            ds_partner_data = datastore_purchase.of_datastore_read(
                ds_partner_obj, [partner_id], ['property_account_position_id', 'user_id', 'company_id'])[0]

            fiscal_position_id = ds_partner_data['property_account_position_id'] and \
                ds_partner_data['property_account_position_id'][0]
            if not fiscal_position_id:
                raise UserError(u"Pas de position fiscale configurée chez le fournisseur !")

            user_id = ds_partner_data['user_id'] and ds_partner_data['user_id'][0]
            if not user_id:
                user_id = client.user_id.id

            company_id = ds_partner_data['company_id'] and ds_partner_data['company_id'][0]
            if not company_id:
                raise UserError(u"Pas de société configurée chez le fournisseur !")

            warehouse_ids = datastore_purchase.of_datastore_search(
                ds_warehouse_obj, [('company_id', '=', company_id)])
            if warehouse_ids:
                warehouse_id = warehouse_ids[0]
            else:
                raise UserError(u"Aucun entrepôt configuré chez le fournisseur !")

            values = {
                'partner_id': partner_id,
                'partner_invoice_id': partner_invoice_id,
                'partner_shipping_id': partner_shipping_id,
                'date_order': self.date_order,
                'client_order_ref': self.customer_id.name,
                'fiscal_position_id': fiscal_position_id,
                'company_id': company_id,
                'user_id': user_id,
                'warehouse_id': warehouse_id,
                'requested_date': self.date_planned,
                'note': self.notes,
                'of_datastore_order': True,
            }

            ds_order_id = datastore_purchase.of_datastore_create(ds_sale_order_obj, values)

            # Création des lignes
            for line in self.order_line:

                # On récupère l'article
                product_ids = datastore_purchase.of_datastore_search(
                    ds_product_obj, [('default_code', '=', line.product_id.default_code)])
                if product_ids:
                    product_id = product_ids[0]
                else:
                    # On prend l'article divers
                    product_id = product_divers_id

                ds_product_data = datastore_purchase.of_datastore_read(
                    ds_product_obj, [product_id], ['uom_id', 'list_price', 'taxes_id'])[0]

                tax_ids = ds_product_data['taxes_id']
                line_tax_ids = []
                ds_fiscal_pos_tax_ids = datastore_purchase.of_datastore_search(
                    ds_fiscal_pos_tax_obj, [('position_id', '=', fiscal_position_id)])
                if ds_fiscal_pos_tax_ids:
                    for tax_id in tax_ids:
                        tax_count = 0
                        for ds_fiscal_pos_tax_id in ds_fiscal_pos_tax_ids:
                            ds_fiscal_pos_tax_data = datastore_purchase.of_datastore_read(
                                ds_fiscal_pos_tax_obj, [ds_fiscal_pos_tax_id], ['tax_src_id', 'tax_dest_id'])[0]
                            tax_src_id = ds_fiscal_pos_tax_data['tax_src_id'][0]
                            tax_dest_id = ds_fiscal_pos_tax_data['tax_dest_id'][0]
                            if tax_src_id == tax_id:
                                tax_count += 1
                                line_tax_ids.append(tax_dest_id)
                        if not tax_count:
                            line_tax_ids.append(tax_id)

                values = {
                    'order_id': ds_order_id,
                    'name': line.name,
                    'product_id': product_id,
                    'product_uom': ds_product_data['uom_id'][0],
                    'product_uom_qty': line.product_qty,
                    'price_unit': ds_product_data['list_price'],
                    'tax_id': [(6, 0, line_tax_ids)],
                }
                datastore_purchase.of_datastore_create(ds_sale_order_line_obj, values)

            # On ajoute un message dans le mail thread
            self.message_post(body=u"%s transmise via commande directe." %
                                   (self.state == 'purchase' and u"Commande fournisseur" or u"Demande de prix"))

            # On passe la commande fournisseur au statut "Demande de prix envoyée"
            if self.state == 'draft':
                self.state = 'sent'

            self.of_sent = True
            self.of_datastore_sent = True
        else:
            raise UserError(u"Aucun connecteur achat trouvé pour ce fournisseur !")
