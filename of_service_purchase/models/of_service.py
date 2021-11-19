# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OfService(models.Model):
    _inherit = 'of.service'

    purchaseorder_ids = fields.Many2many(
        comodel_name='purchase.order', compute='_compute_purchaseorder_ids', string=u"Achats")
    purchase_invoice_ids = fields.One2many(
        comodel_name='account.invoice', compute='_compute_purchase_invoice_ids', string=u"Factures d'achat")
    purchaseorder_count = fields.Integer(string=u"# Achats", compute='_compute_purchaseorder_ids')
    purchase_invoice_count = fields.Integer(string=u"# Factures d'achat", compute='_compute_purchase_invoice_ids')

    @api.depends('line_ids', 'line_ids.purchaseorder_line_id')
    def _compute_purchaseorder_ids(self):
        for service in self:
            service.purchaseorder_ids = service.line_ids.mapped('purchaseorder_line_id').mapped('order_id')
            service.purchaseorder_count = len(service.purchaseorder_ids)

    @api.depends('line_ids', 'line_ids.purchaseorder_line_id.invoice_lines')
    def _compute_purchase_invoice_ids(self):
        for service in self:
            service.purchase_invoice_ids = service.line_ids.mapped('purchaseorder_line_id').mapped('invoice_lines') \
                .mapped('invoice_id')
            service.purchase_invoice_count = len(service.purchase_invoice_ids)

    @api.multi
    def action_view_purchaseorder(self):
        if self.ensure_one():
            return {
                'name': u"Commandes fournisseur",
                'view_mode': 'tree,kanban,form',
                'res_model': 'purchase.order',
                'res_id': self.purchaseorder_ids.ids,
                'domain': "[('id', 'in', %s)]" % self.purchaseorder_ids.ids,
                'type': 'ir.actions.act_window',
            }

    @api.multi
    def action_view_purchase_invoice(self):
        if self.ensure_one():
            return {
                'name': u"Factures fournisseur",
                'view_mode': 'tree,kanban,form',
                'res_model': 'account.invoice',
                'res_id': self.purchase_invoice_ids.ids,
                'domain': "[('id', 'in', %s)]" % self.purchase_invoice_ids.ids,
                'type': 'ir.actions.act_window',
            }

    @api.model
    def make_purchase_order(self):
        self.ensure_one()

        # Ne pas créer de commande si la DI n'est pas validée
        if self.base_state != 'calculated':
            return self.env['of.popup.wizard'].popup_return(
                message=u"Cette demande d'intervention n'est pas validée.")

        # Ne pas créer de commande si pas de lignes
        if not self.line_ids:
            return self.env['of.popup.wizard'].popup_return(
                message=u"Cette demande d'intervention n'a aucune ligne.")

        # Ne pas créer de commande si toutes les lignes sont déjà associées à une commande
        if not self.line_ids.filtered(lambda l: not l.purchaseorder_line_id):
            return self.env['of.popup.wizard'].popup_return(
                message=u"Toutes les lignes sont déjà associées à une commande d'achat.")

        res = {
            'name': u"Demande de prix",
            'view_mode': 'form,tree',
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
        purchase_obj = self.env['purchase.order']
        po_line_obj = self.env['purchase.order.line']
        service_line_obj = self.env['of.service.line']
        if self.company_id:
            my_company_partners = self.company_id.partner_id
        else:
            my_company_partners = self.env['res.company'].search([]).mapped('partner_id')
        lines_by_supplier = {}
        lines_no_supplier = service_line_obj
        lines_i_supply = service_line_obj
        lines_already_done = self.line_ids.filtered(lambda l: l.purchaseorder_line_id)
        # Séparer les ligne par fournisseur, lignes sans fournisseur ignorées pour l'instant
        for line in self.line_ids.filtered(lambda l: not l.purchaseorder_line_id):
            suppliers = line.product_id.seller_ids \
                .filtered(lambda r: (not r.company_id or r.company_id == line.company_id) and
                                    (not r.product_id or r.product_id == line.product_id))
            if suppliers:
                supplier = suppliers[0].name  # supplier.name est un many2one vers res.partner
                if supplier in my_company_partners:
                    lines_i_supply |= line
                else:
                    if supplier not in lines_by_supplier:
                        lines_by_supplier[supplier] = []
                    lines_by_supplier[supplier].append(line)
            else:
                lines_no_supplier |= line
        # Informer si au moins une ligne ne sera pas traitée
        if not self._context.get('of_make_po_validated'):
            validation_message = u""
            if lines_no_supplier or lines_i_supply or lines_already_done:
                validation_message = u"Certaines lignes ne seront pas prises en compte."
            if lines_already_done:
                validation_message += u"\n  - Parce qu'elles ont déjà donné lieu à une commande fournisseur : "
                for line in lines_already_done:
                    validation_message += u"\n\t%s" % line.name
            if lines_i_supply:
                validation_message += u"\n  - Parceque vous en êtes le fournisseur : "
                for line in lines_i_supply:
                    validation_message += u"\n\t%s" % line.name
            if lines_no_supplier:
                validation_message += u"\n  - Parcequ'elles n'ont pas de fournisseur : "
                for line in lines_no_supplier:
                    validation_message += u"\n\t%s" % line.name
            if validation_message:
                context = {'default_message': validation_message, 'default_service_id': self.id}
                res = {
                    'name': u"Veuillez confirmer",
                    'view_mode': 'form,tree',
                    'res_model': 'of.make.po.validation.wizard',
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'context': context,
                }
                return res

        purchase_orders = purchase_obj
        # Vérifier que tous les fournisseurs ont bien une position fiscale, sinon la création de CF echouera
        suppliers_all = lines_by_supplier.keys()
        if not all([s.property_account_position_id for s in suppliers_all]):
            return self.env['of.popup.wizard'].popup_return(
                message=u"Les fournisseurs suivants n'ont pas de position fiscale, "
                        u"ce qui empêche la création de la commande.\n"
                        u"%s" % u", ".join([s.name for s in suppliers_all if not s.property_account_position_id]))
        # Création de chaque CF
        for supplier, lines in lines_by_supplier.iteritems():
            # utilisation de new() pour trigger les onchanges facilement
            purchase_order_new = purchase_obj.new({
                'partner_id': supplier.id,
                'customer_id': self.partner_id.id,
                'origin': self.number,
            })
            purchase_order_new.onchange_partner_id()
            order_values = purchase_order_new._convert_to_write(purchase_order_new._cache)
            purchase_order = purchase_obj.create(order_values)
            purchase_lines = []
            for line in lines:
                line_vals = line.prepare_po_line_vals(purchase_order)
                purchase_lines.append((0, 0, line_vals))
            purchase_order.write({'order_line': purchase_lines})
            purchase_orders |= purchase_order
        # Connecter les lignes à leur ligne de commande correspondante
        for line in self.line_ids.filtered(lambda l: not l.purchaseorder_line_id):
            line.purchaseorder_line_id = po_line_obj.search([('of_service_line_id', '=', line.id)], limit=1)
        # Si plusieurs CF retourner vue liste avec les différentes CF
        # Si une seule, afficher la CF en vue form
        if len(purchase_orders) > 1:
            res['view_mode'] = 'tree,kanban,form'
            res['domain'] = "[('id', 'in', %s)]" % purchase_orders.ids
        elif len(purchase_orders) == 1:
            res['res_id'] = purchase_orders.id

        return res


class OfServiceLine(models.Model):
    _inherit = 'of.service.line'

    purchaseorder_line_id = fields.Many2one(
        comodel_name='purchase.order.line', string=u"Ligne d'achat",
        help=u"Utilisé pour savoir si une commande a été générée pour cette ligne.")
    pol_number = fields.Char(string=u"CF", related='purchaseorder_line_id.order_id.name', readonly=True)

    @api.multi
    def prepare_po_line_vals(self, order):
        purchase_line_obj = self.env['purchase.order.line']
        order_line_new = purchase_line_obj.new({
            'product_id': self.product_id.id,
            'order_id': order.id,
            'of_service_line_id': self.id,
        })
        order_line_new.onchange_product_id()
        order_line_new.update({'product_qty': self.qty})
        order_line_new._onchange_quantity()
        return order_line_new._convert_to_write(order_line_new._cache)
