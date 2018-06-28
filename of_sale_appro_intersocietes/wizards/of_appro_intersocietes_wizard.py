# -*- coding: utf-8 -*-

from odoo import models, api, fields

class OfApproIntersocieteWizard(models.TransientModel):
    _name = "of.appro.intersocietes.wizard"
    _description = "Approvisionnement intersociétés"

    line_ids = fields.One2many('of.appro.intersocietes.wizard.line', 'wizard_id', string="Articles")
    date_planned = fields.Datetime(string=u"Date prévue", required=True)
    company_id = fields.Many2one('res.company', string=u"Société destinataire", required=True)
    rule_id = fields.Many2one('of.sale.appro.rule', string=u"Règle d'approvisionnement", required=True)
    sale_order_origin_id = fields.Many2one('sale.order', string=u"Commande de départ")

    @api.onchange('rule_id')
    def reload_lines_price_marge(self):
        if self.rule_id:
            marge = self.rule_id and self.rule_id.marge_fournisseur or 0
            self.line_ids.reload_price_marge(marge)

    @api.multi
    def _create_procurement(self, line, purchase_line_id, purchase_order):
        procurement_obj = self.env['procurement.order']
        procurement_rule_obj = self.env['procurement.rule']

        move = line.bl_line_id
        data_procurement = move._prepare_procurement_from_move()
        procurement_rule = procurement_rule_obj.search([('action', '=', 'buy'), ('location_id', '=', data_procurement['location_id']), ('company_id', '=', data_procurement['company_id'])])

        data_procurement.update({
            'rule_id': procurement_rule.id,
            'purchase_id': purchase_order.id,
            'purchase_line_id': purchase_line_id.id,
        })

        # Lors de la création d'un procurement, celui-ci créer automatiquement des commandes fournisseurs
        # Pour désactiver la création automatique il faut mettre "procurement_autorun_defer" dans le context
        procurement_id = procurement_obj.with_context(procurement_autorun_defer=True).create(data_procurement)
        line.write({'procurement_id': procurement_id.id})

    @api.multi
    def button_create_orders(self):
        if not self.line_ids:  # Si jamais toutes les lignes ont été supprimées
            return self.env['of.popup.wizard'].popup_return(u"Aucune ligne à approvisionner")

        user_company_src = self.rule_id.user_src_id
        company_src_id = user_company_src.sudo().company_id.partner_id.id

        sale_order_obj = self.env['sale.order'].sudo(user_company_src.id)
        purchase_order_obj = self.env['purchase.order']
        sale_line_obj = self.env['sale.order.line'].sudo(user_company_src.id)
        purchase_line_obj = self.env['purchase.order.line']
        product_pricelist_obj = self.env['product.pricelist']
        # On récupère les listes de prix
        pricelists = product_pricelist_obj.search([('company_id', '=', self.rule_id.company_src_id.id)])
        pricelist = pricelists and [pricelist.id for pricelist in pricelists][0] or False

        # création de la CC et CF
        now = fields.Datetime.now()
        # Les champs obligatoires de la CC
        vals_cc_src = {
            'partner_id': self.rule_id.company_id.partner_id.id,
            'partner_invoice_id': self.rule_id.company_id.partner_id.id,
            'partner_shipping_id': self.rule_id.company_id.partner_id.id,
            'date_order': now,
            'picking_policy': 'direct',
            'company_id': self.rule_id.company_src_id.id,
            'pricelist_id': pricelist or 1,
            'state': 'draft',
        }
        # Les champs obligatoires de la CF
        vals_cf_dest = {
            'partner_id': company_src_id,
            'date_order': now,
            'company_id': self.rule_id.company_id.id,
            'customer_id': self._context.get('partner_id') or self.rule_id.company_src_id.partner_id.id,
            'sale_order_id': self.sale_order_origin_id.id,
            'currency_id': 1,
            'date_planned': self.date_planned,
            'state': 'draft',
        }
        sale_order = sale_order_obj.create(vals_cc_src)
        purchase_order = purchase_order_obj.create(vals_cf_dest)

        # Création des lignes de la CC et CF
        marge_ratio = 100.0 - self.rule_id.marge_fournisseur
        for line in self.line_ids:
            product = line.product_id
            product_uom = line.product_uom_id
            product_qty = line.product_qty  # pour CF -> product_qty, pour CC -> product_uom_qty
            name = product.name_get()[0][1]  # name correspond à la description, trouvé dans sale.order.line, product_id_change()
            if product.description_sale:
                name += '\n' + product.description_sale
            # Les champs obligatoires des lignes de la CC
            sale_line_obj.create({
                'product_id': product.id,
                'of_is_kit': product.of_is_kit,
                'of_pricing': product.of_pricing,
                'product_uom_qty': product_qty,
                'product_uom': product_uom.id,
                'order_id': sale_order.id,
                'price_unit': marge_ratio and product.standard_price * 100.0 / marge_ratio,
                'name': name,
                'customer_lead': product.sale_delay,
            })
            # Les champs obligatoires des lignes de la CF
            purchase_line_id = purchase_line_obj.create({
                'product_id': product.id,
                'name': name,
                'product_uom': product_uom.id,
                'product_qty': product_qty,
                'order_id': purchase_order.id,
                'price_unit': marge_ratio and product.standard_price * 100.0 / marge_ratio,
                'date_planned': self.date_planned,
            })
            line.bl_line_id.write({'state': 'waiting'})
            # Ajout de la création de procurement pour lier le BL et le BR de la commande fournisseur créée
            self._create_procurement(line, purchase_line_id, purchase_order)
        message = "La commande client " + sale_order.name + " et la commande fournisseur " + purchase_order.name + u" ont été créées."
        return self.env['of.popup.wizard'].popup_return(message)

class OfApproIntersocietesWizardLine(models.TransientModel):
    _name = "of.appro.intersocietes.wizard.line"

    product_id = fields.Many2one('product.product', string='Article')
    product_qty = fields.Float(string=u'Qté', default=0)
    product_uom_id = fields.Many2one('product.uom', string=u'Unité de mesure')
    wizard_id = fields.Many2one('of.appro.intersocietes.wizard', string="wizard")
    price = fields.Float(string='Prix')
    price_marge = fields.Float(string=u'Prix majoré')
    marge = fields.Float(string="Marge", default=0)
    bl_line_id = fields.Many2one('stock.move', string="Ligne du bon de livraison")

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        for line in self:
            if line.product_id:
                vals = {
                    'price': line.product_id.standard_price,
                    'product_uom_id': line.product_id.uom_id.id,
                }
                line.update(vals)  # utile pour rafraichir les valeurs sur la vue
                line.reload_price_marge(line.marge or 0)

    @api.multi
    def reload_price_marge(self, marge):
        for line in self:  # Est nécessaire pour le onchange('rule_id') de OfApproIntersocieteWizard
            marge_ratio = 100.0 - marge
            vals = {
                'marge': marge,
                'price_marge': marge_ratio and line.price * 100.0 / marge_ratio,
            }
            line.update(vals)  # voir méthode product_id_change
