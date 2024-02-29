# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OfService(models.Model):
    _inherit = 'of.service'

    purchaseorder_ids = fields.Many2many(
        comodel_name='purchase.order', compute='_compute_purchaseorder_ids', string=u"Achats")
    gb_purchaseorder_id = fields.Many2one(
        comodel_name='purchase.order', compute=lambda s: None, search='_search_gb_purchaseorder_id',
        string="Commandes d'achat", of_custom_groupby=True)
    purchase_invoice_ids = fields.One2many(
        comodel_name='account.invoice', compute='_compute_purchase_invoice_ids', string=u"Factures d'achat")
    gb_purchase_invoice_id = fields.Many2one(
        comodel_name='account.invoice', compute=lambda s: None, search='_search_gb_purchase_invoice_id',
        string="Factures d'achat", of_custom_groupby=True)
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

    @api.model
    def _search_gb_purchaseorder_id(self, operator, operand):
        if operator == '=' and operand is False:
            return [
                '|',
                ('line_ids', '=', False),
                ('line_ids.purchaseorder_line_id', '=', False),
            ]
        return [('line_ids.purchaseorder_line_id.order_id.id', operator, operand)]

    @api.model
    def _search_gb_purchase_invoice_id(self, operator, operand):
        if operator == '=' and operand is False:
            return [
                '|', '|',
                ('line_ids', '=', False),
                ('line_ids.purchaseorder_line_id', '=', False),
                ('line_ids.purchaseorder_line_id.invoice_lines', '=', False),
            ]
        return [('line_ids.purchaseorder_line_id.invoice_lines.invoice_id', operator, operand)]

    @api.model
    def _read_group_process_groupby(self, gb, query):
        """ Ajout de la possibilité de regrouper par commande(s) d'achat(s)
            ou facture(s) de commande(s) d'achat(s)
        """
        if gb not in ('gb_purchaseorder_id', 'gb_purchase_invoice_id'):
            return super(OfService, self)._read_group_process_groupby(gb, query)
        elif gb == 'gb_purchaseorder_id':
            alias, _ = query.add_join(
                (self._table, 'of_service_line', 'id', 'service_id', '1'),
                implicit=False, outer=True,
            )
            alias2, _ = query.add_join(
                (alias, 'purchase_order_line', 'purchaseorder_line_id', 'id', '2'),
                implicit=False, outer=True,
            )
            qualified_field = '"%s".order_id' % (alias2,)
        elif gb == 'gb_purchase_invoice_id':
            alias, _ = query.add_join(
                (self._table, 'of_service_line', 'id', 'service_id', '1'),
                implicit=False, outer=True,
            )
            alias2, _ = query.add_join(
                (alias, 'purchase_order_line', 'purchaseorder_line_id', 'id', '2'),
                implicit=False, outer=True,
            )
            alias3, _ = query.add_join(
                (alias2, 'account_invoice_line', 'id', 'purchase_line_id', '3'),
                implicit=False, outer=True,
            )
            qualified_field = '"%s".invoice_id' % (alias3,)
        return {
            'field': gb,
            'groupby': gb,
            'type': 'many2one',
            'display_format': None,
            'interval': None,
            'tz_convert': False,
            'qualified_field': qualified_field
        }

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

    @api.multi
    def make_purchase_order(self, supplier_mode='product_supplier'):
        purchase_obj = self.env['purchase.order']
        po_line_obj = self.env['purchase.order.line']
        service_line_obj = self.env['of.service.line']
        popup_wizard_obj = self.env['of.popup.wizard']
        res_company_obj = self.env['res.company']

        purchase_orders = purchase_obj

        for service in self:

            service_name = service.number or service.titre or "ID : %s" % service.id

            # Ne pas créer de commande si la DI n'est pas validée
            if service.base_state != 'calculated':
                return popup_wizard_obj.popup_return(
                    message=u"La demande d'intervention %s n'est pas validée." % service_name)

            # Ne pas créer de commande si pas de lignes
            if not service.line_ids:
                return popup_wizard_obj.popup_return(
                    message=u"La demande d'intervention %s n'a aucune ligne." % service_name)

            # Ne pas créer de commande si toutes les lignes sont déjà associées à une commande
            if not service.line_ids.filtered(lambda l: not l.purchaseorder_line_id):
                return popup_wizard_obj.popup_return(
                    message=u"Toutes les lignes de la demande d'intervention %s sont déjà associées à une commande "
                            u"d'achat." % service_name)

            res = {
                'name': u"Demande de prix",
                'view_mode': 'form,tree',
                'res_model': 'purchase.order',
                'type': 'ir.actions.act_window',
                'target': 'current',
            }

            if service.company_id:
                my_company_partners = service.company_id.partner_id
            else:
                my_company_partners = res_company_obj.search([]).mapped('partner_id')

            lines_by_supplier = {}
            lines_no_supplier = service_line_obj
            lines_i_supply = service_line_obj
            lines_already_done = service.line_ids.filtered(lambda l: l.purchaseorder_line_id)

            # Séparer les ligne par fournisseur, lignes sans fournisseur ignorées pour l'instant
            for line in service.line_ids.filtered(lambda l: not l.purchaseorder_line_id):
                supplier = line._get_po_supplier(supplier_mode=supplier_mode)
                if supplier:
                    if supplier in my_company_partners:
                        lines_i_supply |= line
                    else:
                        if supplier not in lines_by_supplier:
                            lines_by_supplier[supplier] = []
                        lines_by_supplier[supplier].append(line)
                else:
                    lines_no_supplier |= line

            # Informer si au moins une ligne ne sera pas traitée
            if len(self) == 1 and not self._context.get('of_make_po_validated'):
                validation_message = u""
                if lines_no_supplier or lines_i_supply or lines_already_done:
                    validation_message = u"Certaines lignes ne seront pas prises en compte."
                if lines_already_done:
                    validation_message += u"\n  - Parce qu'elles ont déjà donné lieu à une commande fournisseur : "
                    for line in lines_already_done:
                        validation_message += u"\n\t%s" % line.product_id.name
                if lines_i_supply:
                    validation_message += u"\n  - Parce que vous en êtes le fournisseur : "
                    for line in lines_i_supply:
                        validation_message += u"\n\t%s" % line.product_id.name
                if lines_no_supplier:
                    validation_message += u"\n  - Parce qu'elles n'ont pas de fournisseur : "
                    for line in lines_no_supplier:
                        validation_message += u"\n\t%s" % line.product_id.name
                if validation_message:
                    context = {
                        'default_message': validation_message,
                        'default_service_id': self.id,
                        'active_model': 'of.service',
                        'active_id': self.id,
                        'supplier_mode': supplier_mode,
                    }
                    res = {
                        'name': u"Veuillez confirmer",
                        'view_mode': 'form,tree',
                        'res_model': 'of.make.po.validation.wizard',
                        'type': 'ir.actions.act_window',
                        'target': 'new',
                        'context': context,
                    }
                    return res

            # Vérifier que tous les fournisseurs ont bien une position fiscale, sinon la création de CF echouera
            suppliers_all = lines_by_supplier.keys()
            if not all([s.property_account_position_id for s in suppliers_all]):
                return popup_wizard_obj.popup_return(
                    message=u"Les fournisseurs suivants n'ont pas de position fiscale, "
                            u"ce qui empêche la création de la commande pour la demande d'intervention %s.\n"
                            u"%s" % (service_name,
                                     u", ".join([s.name for s in suppliers_all if not s.property_account_position_id])))

            # Création de chaque CF
            for supplier, lines in lines_by_supplier.iteritems():
                # utilisation de new() pour trigger les onchanges facilement
                purchase_order_vals = service.get_purchase_order_vals(supplier)
                purchase_order_new = purchase_obj.new(purchase_order_vals)
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
            for line in service.line_ids.filtered(lambda l: not l.purchaseorder_line_id):
                line.purchaseorder_line_id = po_line_obj.search([('of_service_line_id', '=', line.id)], limit=1)

        # Si plusieurs CF retourner vue liste avec les différentes CF
        # Si une seule, afficher la CF en vue form
        if len(purchase_orders) > 1:
            res['view_mode'] = 'tree,kanban,form'
            res['domain'] = "[('id', 'in', %s)]" % purchase_orders.ids
        elif len(purchase_orders) == 1:
            res['res_id'] = purchase_orders.id

        return res

    @api.multi
    def get_purchase_order_vals(self, supplier):
        return {
            'partner_id': supplier.id,
            'customer_id': self.partner_id.id,
            'origin': self.number,
            'of_date_next': self.date_next,
            'of_date_end': self.date_fin,
        }


class OfServiceLine(models.Model):
    _inherit = 'of.service.line'

    purchaseorder_line_id = fields.Many2one(
        comodel_name='purchase.order.line', string=u"Ligne d'achat",
        help=u"Utilisé pour savoir si une commande a été générée pour cette ligne.")
    po_number = fields.Char(
        string=u"Numéro de commande fournisseur", related='purchaseorder_line_id.order_id.name', readonly=True)

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

    @api.multi
    def _get_po_supplier(self, supplier_mode='product_supplier'):
        if supplier_mode == 'product_supplier':
            suppliers = self.product_id.seller_ids.filtered(
                lambda r: (not r.company_id or r.company_id == self.company_id) and
                          (not r.product_id or r.product_id == self.product_id))
            if suppliers:
                return suppliers[0].name  # supplier.name est un many2one vers res.partner
        return False
