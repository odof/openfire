# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

class OfAnalyseChantierInherit(models.AbstractModel):
    _name = 'of.analyse.chantier.inherit'

    name = fields.Char(compute="_compute_name")
    chantier_id = fields.Many2one('of.analyse.chantier', string="Chantier", required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string="Article")
    product_name = fields.Char(string=u"Désignation de l'article", related="product_id.name")

    order_line_ids = fields.Many2many('sale.order.line', string="Ligne de commande")
    invoice_line_ids = fields.Many2many('account.invoice.line', string="Ligne de facture")
    saleorder_kit_line_ids = fields.Many2many('of.saleorder.kit.line', string="Composant kit de commande")
    invoice_kit_line_ids = fields.Many2many('of.invoice.kit.line', string="Composant kit de facture")
    pack_operation_id = fields.Many2one('stock.pack.operation', string="Ligne de BL")

    subtotal = fields.Float(string="PV HT")

    qty_ordered = fields.Float(string=u"Qté commandée")
    qty_delivered = fields.Float(string=u"Qté livrée")
    qty_invoiced = fields.Float(string=u"Qté facturée")
    price_unit = fields.Float(string="PVU HT")

    @api.depends('order_line_ids', 'invoice_line_ids', 'pack_operation_id')
    def _compute_name(self):
        for line in self:
            if line.invoice_kit_line_ids:
                line.name = "%s, %s" % (" ".join(line.invoice_kit_line_ids.mapped('invoice_id').mapped('display_name')), 'kit')
            elif line.invoice_line_ids:
                line.name = " ".join(line.invoice_line_ids.mapped('invoice_id').mapped('display_name'))
            elif line.saleorder_kit_line_ids:
                line.name = "%s, %s" % (" ".join(line.saleorder_kit_line_ids.mapped('order_id').mapped('display_name')), 'kit')
            elif line.order_line_ids:
                line.name = " ".join(line.order_line_ids.mapped('order_id').mapped('display_name'))
            elif line.pack_operation_id:
                line.name = "%s" % line.pack_operation_id.picking_id.name

    def _get_values_from_order_lines(self):
        return {
            'invoice_line_ids' : [(6, 0, self.order_line_ids.mapped('invoice_lines')._ids)],
            'qty_ordered': sum(self.order_line_ids.mapped('product_uom_qty')),
            'qty_delivered': sum(self.order_line_ids.mapped('qty_delivered')),
            'qty_invoiced': sum(self.order_line_ids.mapped('qty_invoiced')),
            'product_id': self.order_line_ids.mapped('product_id').id,
            'price_unit': sum(self.order_line_ids.mapped('price_unit')) / len(self.order_line_ids),
            'subtotal': sum(self.order_line_ids.mapped('price_subtotal')),
            }

    def _get_values_from_order_kit_lines(self):
        order_line = self.saleorder_kit_line_ids.mapped('kit_id').order_line_id
        invoice_lines = order_line.mapped('invoice_lines')
        invoice_kit_lines = invoice_lines.mapped('kit_id').mapped('kit_line_ids').filtered(
            lambda l: l.product_id.id == self.saleorder_kit_line_ids.mapped('product_id').id)
        return {
            'invoice_line_ids': [(6, 0, invoice_lines._ids)],
            'invoice_kit_line_ids': [(6, 0, invoice_kit_lines._ids)],
            'order_line_ids': [(6, 0, [order_line.id])],
            'qty_ordered': sum(self.saleorder_kit_line_ids.mapped('qty_total')),
            'qty_delivered': sum(self.saleorder_kit_line_ids.mapped('qty_delivered')),
            'qty_invoiced': sum(self.saleorder_kit_line_ids.filtered('invoiced').mapped('qty_total')) or 0,
            'product_id': self.saleorder_kit_line_ids.mapped('product_id').id,
            'subtotal': sum(self.saleorder_kit_line_ids.mapped('price_total')),
            'price_unit': sum(self.saleorder_kit_line_ids.mapped('price_unit')) / len(self.saleorder_kit_line_ids),
            }

    def _get_values_from_invoice_lines(self):
        invoice_lines = self.invoice_line_ids
        order_lines = invoice_lines.mapped('of_order_line_ids')
        return {
            'order_line_ids' : [(6, 0, order_lines._ids)],
            'qty_ordered': order_lines and sum(order_lines.mapped('product_uom_qty')) or 0,
            'qty_delivered': order_lines and sum(order_lines.mapped('qty_delivered')) or 0,
            'qty_invoiced': sum(self.invoice_line_ids.mapped('quantity')),
            'product_id': self.invoice_line_ids.mapped('product_id').id,
            'price_unit': sum(self.invoice_line_ids.mapped('price_unit')) / len(self.invoice_line_ids),
            'subtotal': sum(self.invoice_line_ids.mapped('price_subtotal_signed')),
            }

    def _get_values_from_invoice_kit_lines(self):
        invoice_line = self.invoice_kit_line_ids.mapped('kit_id').invoice_line_id
        order_lines = invoice_line.mapped('of_order_line_ids')
        order_kit_lines = order_lines.mapped('kit_id').mapped('kit_line_ids').filtered(
            lambda l: l.product_id.id == self.invoice_kit_line_ids.mapped('product_id').id)
        return {
            'invoice_line_ids': [(6, 0, [invoice_line.id])],
            'saleorder_kit_line_ids': [(6, 0, order_kit_lines._ids)],
            'order_line_ids': [(6, 0, order_lines._ids)],
            'qty_ordered': order_kit_lines and sum(order_kit_lines.mapped('qty_total')) or 0,
            'qty_delivered': order_kit_lines and sum(order_kit_lines.mapped('qty_delivered')) or 0,
            'qty_invoiced': sum(self.invoice_kit_line_ids.mapped('qty_total')),
            'product_id': self.invoice_kit_line_ids.mapped('product_id').id,
            'price_unit': sum(self.invoice_kit_line_ids.mapped('price_unit')) / len(self.invoice_kit_line_ids),
            'subtotal': sum(self.invoice_kit_line_ids.mapped('price_total')),
            }

    def _get_values_from_pack_operation(self):
        operation = self.pack_operation_id
        return {
            'qty_ordered': 0,
            'qty_delivered': operation.qty_done,
            'qty_invoiced': 0,
            'product_id': operation.product_id.id,
            'subtotal': 0,
            }

    def get_line_dict_from_order_lines(self, order_lines, chantier):
        return {
            'chantier_id': chantier.id,
            'order_line_ids': [(4, line.id) for line in order_lines],
            'invoice_line_ids' : [(4, line.id) for line in order_lines.mapped('invoice_lines')],
            'qty_ordered': sum(order_lines.mapped('product_uom_qty')),
            'qty_delivered': sum(order_lines.mapped('qty_delivered')),
            'qty_invoiced': sum(order_lines.mapped('qty_invoiced')),
            'product_id': order_lines.mapped('product_id').id,
            'subtotal': sum(order_lines.mapped('price_subtotal')),
            }

    def get_line_dict_from_order_kit_lines(self, kit_lines, chantier):
        order_line = kit_lines.mapped('kit_id').order_line_id
        invoice_lines = order_line.mapped('invoice_lines')
        invoice_kit_lines = invoice_lines.mapped('kit_id').mapped('kit_line_ids').filtered(
            lambda l: l.product_id.id == kit_lines.mapped('product_id').id)
        return {
            'chantier_id': chantier.id,
            'saleorder_kit_line_ids': [(4, line.id) for line in kit_lines],
            'invoice_line_ids': [(4, line.id) for line in invoice_lines],
            'invoice_kit_line_ids': [(4, line.id) for line in invoice_kit_lines],
            'order_line_ids': [(4, order_line.id)],
            'qty_ordered': sum(kit_lines.mapped('qty_total')),
            'qty_delivered': sum(kit_lines.mapped('qty_delivered')),
            'qty_invoiced': sum(kit_lines.filtered('invoiced').mapped('qty_total')) or 0,
            'product_id': kit_lines.mapped('product_id').id,
            'subtotal': sum(kit_lines.mapped('price_total')),
            }

    def get_line_dict_from_invoice_lines(self, invoice_lines, chantier):
        order_lines = invoice_lines.mapped('of_order_line_ids')
        return {
            'chantier_id': chantier.id,
            'invoice_line_ids': [(4, line.id) for line in invoice_lines],
            'order_line_ids' : [(4, line.id) for line in order_lines],
            'qty_ordered': order_lines and sum(order_lines.mapped('product_uom_qty')) or 0,
            'qty_delivered': order_lines and sum(order_lines.mapped('qty_delivered')) or 0,
            'qty_invoiced': sum(invoice_lines.mapped('quantity')),
            'product_id': invoice_lines.mapped('product_id').id,
            'subtotal': sum(invoice_lines.mapped('price_subtotal_signed')),
            }

    def get_line_dict_from_invoice_kit_lines(self, kit_lines, chantier):
        invoice_line = kit_lines.mapped('kit_id').invoice_line_id
        order_lines = invoice_line.mapped('of_order_line_ids')
        order_kit_lines = order_lines.mapped('kit_id').mapped('kit_line_ids').filtered(lambda l: l.product_id.id ==  kit_lines.mapped('product_id').id)
        return {
            'chantier_id': chantier.id,
            'invoice_kit_line_ids': [(4, line.id) for line in kit_lines],
            'invoice_line_ids': [(4, invoice_line.id)],
            'saleorder_kit_line_ids': [(4, line.id) for line in order_kit_lines],
            'order_line_ids': [(4, line.id) for line in order_lines],
            'qty_ordered': order_kit_lines and sum(order_kit_lines.mapped('qty_total')) or 0,
            'qty_delivered': order_kit_lines and sum(order_kit_lines.mapped('qty_delivered')) or 0,
            'qty_invoiced': sum(kit_lines.mapped('qty_total')),
            'product_id': kit_lines.mapped('product_id').id,
            'subtotal': sum(kit_lines.mapped('price_total')),
            }

    def get_line_dict_from_pack_operation(self, operation, chantier):
        return {
            'pack_operation_id': operation.id,
            'chantier_id': chantier.id,
            'qty_ordered': 0,
            'qty_delivered': operation.qty_done,
            'qty_invoiced': 0,
            'product_id': operation.product_id.id,
            'subtotal': 0,
            }

    def create_line_from_order_lines(self, order_line, chantier):
        new_line = self.create(self.get_line_dict_from_order_lines(order_line, chantier))
        return new_line

    def create_line_from_order_kit_lines(self, kit_line, chantier):
        new_line = self.create(self.get_line_dict_from_order_kit_lines(kit_line, chantier))
        return new_line

    def create_line_from_invoice_lines(self, invoice_line, chantier):
        new_line = self.create(self.get_line_dict_from_invoice_lines(invoice_line, chantier))
        return new_line

    def create_line_from_invoice_kit_lines(self, kit_line, chantier):
        new_line = self.create(self.get_line_dict_from_invoice_kit_lines(kit_line, chantier))
        return new_line

    def create_line_from_pack_operation(self, operation, chantier):
        new_line = self.create(self.get_line_dict_from_pack_operation(operation, chantier))
        return new_line

    def synchroniser(self):
        if self.invoice_kit_line_ids:
            self.update(self._get_values_from_invoice_kit_lines())
        elif self.invoice_line_ids:
            self.update(self._get_values_from_invoice_lines())
        elif self.saleorder_kit_line_ids:
            self.update(self._get_values_from_order_kit_lines())
        elif self.order_line_ids:
            self.update(self._get_values_from_order_lines())
        elif self.pack_operation_id:
            self.update(self._get_values_from_pack_operation())

class OfAnalyseChantierLine(models.AbstractModel):
    _name = "of.analyse.chantier.line"
    _inherit = 'of.analyse.chantier.inherit'
    _order_ = 'in_use desc, subtotal desc'

    methode_cout = fields.Selection([('ach', u'ACH'),
                                     ('cout', u'COUT'),
                                     ('ana', u'ANA')], string=u"Méthode coût", required=True)
    subtotal_compute = fields.Float(string="PV HT", compute="_compute_subtotal", store=True)
    purchase_price_compute = fields.Float(string=u"Coût total", compute="_compute_purchase_price", inverse="_inverse_purchase_price", store=True)
    purchase_price = fields.Float(string=u"Coût total")
    margin = fields.Float(string="Marge", compute="compute_marge", store=True)
    margin_pc = fields.Float(string="Marge (%)", compute="compute_marge", store=True)
    in_use = fields.Boolean(string="Prendre en compte", default=True)

    @api.multi
    def toggle_use(self):
        self.in_use = not self.in_use

    @api.depends('subtotal', 'qty_ordered', 'purchase_price', 'in_use')
    def compute_marge(self):
        for line in self:
            if not line.in_use:
                line.update({'margin': 0, 'margin_pc': 0})
                continue
            marge = line.subtotal - line.purchase_price
            marge_percent = marge * 100 / line.subtotal if line.subtotal != 0 else 0
            line.update({'margin': marge, 'margin_pc': marge_percent})

    @api.depends('subtotal', 'in_use')
    def _compute_subtotal(self):
        for line in self:
            if not line.in_use:
                line.subtotal_compute = 0
                continue
            line.subtotal_compute = line.subtotal

    @api.depends('purchase_price', 'in_use')
    def _compute_purchase_price(self):
        for line in self:
            if not line.in_use:
                line.purchase_price_compute = 0
                continue
            line.purchase_price_compute = line.purchase_price

    def _inverse_purchase_price(self):
        for line in self:
            if not line.in_use:
                continue
            line.purchase_price = line.purchase_price_compute

    def get_purchase_price(self, qty):
        if self.methode_cout == 'cout':
            return self.product_id.get_cost() * qty
        elif self.methode_cout == 'ach':
            if self.saleorder_kit_line_ids:
                purchase_lines = self.saleorder_kit_line_ids.mapped('procurement_ids').mapped('move_ids').mapped('move_orig_ids').mapped(
                    'purchase_line_id')
            elif self.order_line_ids:
                purchase_lines = self.order_line_ids.mapped('procurement_ids').mapped('move_ids').mapped('move_orig_ids').mapped('purchase_line_id')
            else:
                return self.product_id.get_cost() * qty
            return sum(purchase_lines.mapped('price_subtotal'))
        else:
            return self.purchase_price

    @api.onchange('methode_cout', 'product_id')
    def onchange_methode_cout(self):
        self.ensure_one()
        if self.invoice_line_ids or self.invoice_kit_line_ids:
            self.purchase_price = self.get_purchase_price(self.qty_invoiced)
        elif self.order_line_ids or self.saleorder_kit_line_ids:
            self.purchase_price = self.get_purchase_price(self.qty_ordered)
        elif self.pack_operation_id:
            self.purchase_price = self.get_purchase_price(self.qty_delivered)
        else:
            return

    def synchroniser(self):
        super(OfAnalyseChantierLine, self).synchroniser()
        self.onchange_methode_cout()

    def get_line_dict_from_order_lines(self, order_line, chantier):
        vals = super(OfAnalyseChantierLine, self).get_line_dict_from_order_lines(order_line, chantier)
        return dict(vals, methode_cout=chantier.methode_cout)

    def get_line_dict_from_order_kit_lines(self, kit_line, chantier):
        vals = super(OfAnalyseChantierLine, self).get_line_dict_from_order_kit_lines(kit_line, chantier)
        return dict(vals, methode_cout=chantier.methode_cout)

    def get_line_dict_from_invoice_lines(self, invoice_line, chantier):
        vals = super(OfAnalyseChantierLine, self).get_line_dict_from_invoice_lines(invoice_line, chantier)
        return dict(vals, methode_cout=chantier.methode_cout)

    def get_line_dict_from_invoice_kit_lines(self, kit_line, chantier):
        vals = super(OfAnalyseChantierLine, self).get_line_dict_from_invoice_kit_lines(kit_line, chantier)
        return dict(vals, methode_cout=chantier.methode_cout)

    def get_line_dict_from_pack_operation(self, operation, chantier):
        vals = super(OfAnalyseChantierLine, self).get_line_dict_from_pack_operation(operation, chantier)
        return dict(vals, methode_cout=chantier.methode_cout)

    def create_line_from_order_lines(self, order_line, chantier):
        new_line = super(OfAnalyseChantierLine, self).create_line_from_order_lines(order_line, chantier)
        new_line.onchange_methode_cout()
        return new_line

    def create_line_from_order_kit_lines(self, kit_line, chantier):
        new_line = super(OfAnalyseChantierLine, self).create_line_from_order_kit_lines(kit_line, chantier)
        new_line.onchange_methode_cout()
        return new_line

    def create_line_from_invoice_lines(self, invoice_line, chantier):
        new_line = super(OfAnalyseChantierLine, self).create_line_from_invoice_lines(invoice_line, chantier)
        new_line.onchange_methode_cout()
        return new_line

    def create_line_from_invoice_kit_lines(self, kit_line, chantier):
        new_line = super(OfAnalyseChantierLine, self).create_line_from_invoice_kit_lines(kit_line, chantier)
        new_line.onchange_methode_cout()
        return new_line

    def create_line_from_pack_operation(self, operation, chantier):
        new_line = super(OfAnalyseChantierLine, self).create_line_from_pack_operation(operation, chantier)
        new_line.onchange_methode_cout()
        return new_line

class OfAnalyseChantierService(models.Model):
    _name = "of.analyse.chantier.service"
    _inherit = 'of.analyse.chantier.line'
    _order_ = 'in_use desc, subtotal desc'

    # methode_cout = fields.Selection(selection_add=[('intervention', 'INTERVENTION')], string=u"Méthode coût", required=True)
    #
    # def get_purchase_price(self, qty):
    #     if self.methode_cout == 'ach':
    #         return self.product_id.of_seller_price * qty
    #     elif self.methode_cout == 'cout':
    #         if self.saleorder_kit_line_ids:
    #             purchase_lines = self.saleorder_kit_line_ids.mapped('procurement_ids').mapped('move_ids').mapped('move_orig_ids').mapped(
    #                 'purchase_line_id')
    #         elif self.order_line_ids:
    #             purchase_lines = self.order_line_ids.mapped('procurement_ids').mapped('move_ids').mapped('move_orig_ids').mapped('purchase_line_id')
    #         else:
    #             return self.product_id.of_seller_price * qty
    #         return sum(purchase_lines.mapped('price_subtotal'))
    #     elif self.methode_cout == 'intervention':
    #         return 0
    #     else:
    #         return self.purchase_price


class OfAnalyseChantierProduct(models.Model):
    _name = "of.analyse.chantier.product"
    _inherit = 'of.analyse.chantier.line'
    _order_ = 'in_use desc, subtotal desc'


class OfAnalyseChantierRemise(models.Model):
    _name = "of.analyse.chantier.remise"
    _inherit = 'of.analyse.chantier.inherit'
    _order_ = 'subtotal desc'

    active = fields.Boolean(string="Active", default=True)
    affectation = fields.Selection([('product', 'Produits'), ('service', 'Services')], string="Affectation", required=True, default='product')

    @api.multi
    def change_use(self):
        self.affectation = 'product' if self.affectation == 'service' else 'service'


class OfAnalyseChantier(models.Model):
    _name = "of.analyse.chantier"

    name = fields.Char(string="Nom", compute="_compute_name", store=True)
    state = fields.Selection(string=u"État", selection=[('draft', 'En cours'), ('done', u'Validée')], default='draft')
    partner_id = fields.Many2one(
        comodel_name='res.partner', string="Partenaire", compute="_compute_partner", store=True)
    order_ids = fields.One2many('sale.order', 'of_analyse_id', string="Commandes")
    invoice_ids = fields.One2many('account.invoice', 'of_analyse_id', string="Factures")
    picking_ids = fields.One2many('stock.picking', 'of_analyse_id', string="Bons de livraisons")
    methode_cout = fields.Selection([('ach', u'ACH'),
                                     ('cout', u'COUT'),
                                     ('ana', u'ANA')], string=u"Méthode coût", required=True, default='ach')

    product_line_ids = fields.One2many('of.analyse.chantier.product', 'chantier_id', string="Produits")
    service_line_ids = fields.One2many('of.analyse.chantier.service', 'chantier_id', string="Services")
    remise_ids = fields.One2many('of.analyse.chantier.remise', 'chantier_id', string="Remises", context={'active_test':False})

    cout_chantier = fields.Float(string="Coût du chantier", compute="_compute_marge", store=True)
    vente_chantier = fields.Float(string="Vente du chantier", compute="_compute_marge", store=True)

    cout_produit_total = fields.Float(string="Coût total produits", compute="_compute_produit", store=True)
    cout_produit = fields.Float(string="Coût des produits", compute="_compute_produit", store=True)
    cout_produit_additionnels = fields.Float(string="Coût des produits additionnels", compute="_compute_produit", store=True)
    vente_produit_total = fields.Float(string="Vente total produits", compute="_compute_produit", store=True)
    vente_produit = fields.Float(string="Vente des produits", compute="_compute_produit", store=True)
    vente_produit_additionnels = fields.Float(string="Vente des produits additionnels", compute="_compute_produit", store=True)

    cout_service_total = fields.Float(string="Coût total services", compute="_compute_service", store=True)
    cout_service = fields.Float(string="Coût des services", compute="_compute_service", store=True)
    cout_service_additionnels = fields.Float(string="Coût des services additionnels", compute="_compute_service", store=True)
    vente_service_total = fields.Float(string="Vente total services", compute="_compute_service", store=True)
    vente_service = fields.Float(string="Vente des services", compute="_compute_service", store=True)
    vente_service_additionnels = fields.Float(string="Vente des services additionnels", compute="_compute_service", store=True)

    marge_brute = fields.Float(string="Marge brute", compute="_compute_marge", store=True)
    marge_brute_pc = fields.Float(string="Marge brute (%)", compute="_compute_marge", store=True)
    marge_semi_nette = fields.Float(string="Marge semi-nette", compute="_compute_marge", store=True)
    marge_semi_nette_pc = fields.Float(string="Marge semi-nette (%)", compute="_compute_marge", store=True)
    marge_nette = fields.Float(string="Marge nette", compute="_compute_marge", store=True)
    marge_nette_pc = fields.Float(string="Marge nette (%)", compute="_compute_marge", store=True)

    view_qty = fields.Boolean(string=u"Voir les quantitées", default=True)

    intervention_ids = fields.Many2many('of.planning.intervention', string=u"Poses liées", compute="_compute_intervention_ids")

    @api.multi
    def action_done(self):
        self.state = 'done'

    @api.depends('order_ids')
    def _compute_intervention_ids(self):
        for analyse in self:
            analyse.intervention_ids = analyse.order_ids.mapped('intervention_ids').filtered(lambda i: i.state in ('draft, confirm, done, unfinished'))

    @api.depends('partner_id', 'order_ids', 'invoice_ids')
    def _compute_name(self):
        for analyse in self:
            partner = analyse.partner_id
            orders = analyse.order_ids
            invoices = analyse.invoice_ids
            analyse.name = "%s / %s / %s" % (partner.name,
                                             " - ".join([name or '' for name in orders.mapped('name')]),
                                             " - ".join([name or '' for name in invoices.mapped('move_name')]))


    def toggle_view_qty(self):
        """ Permet d'afficher/masquer les quantitées
        """
        self.view_qty = not self.view_qty
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            }

    def button_deliver_all(self):
        for line in self.product_line_ids:
            line.qty_delivered = line.qty_ordered
        for line in self.service_line_ids:
            line.qty_delivered = line.qty_ordered

    def button_dummy(self):
        return {'type': 'ir.actions.do_nothing'}

    @api.depends('product_line_ids.subtotal_compute', 'product_line_ids.purchase_price',
                 'remise_ids.affectation')
    def _compute_produit(self):
        for analyse in self:
            product_used = analyse.product_line_ids.filtered('in_use').filtered(lambda l: l.order_line_ids)
            product_added = analyse.product_line_ids.filtered('in_use').filtered(
                lambda l: l.invoice_line_ids and not l.order_line_ids)
            analyse.cout_produit = sum(product_used.mapped('purchase_price_compute'))
            analyse.cout_produit_additionnels = sum(product_added.mapped('purchase_price_compute'))
            analyse.cout_produit_total = analyse.cout_produit + analyse.cout_produit_additionnels

            analyse.vente_produit = sum(product_used.mapped('subtotal'))
            analyse.vente_produit_additionnels = sum(product_added.mapped('subtotal'))
            analyse.vente_produit_total = analyse.vente_produit + analyse.vente_produit_additionnels + sum(
                analyse.remise_ids.filtered(lambda r: r.active and r.affectation == 'product').mapped('subtotal'))

    @api.depends('service_line_ids.subtotal_compute', 'service_line_ids.purchase_price',
                 'remise_ids.affectation')
    def _compute_service(self):
        for analyse in self:
            service_used = analyse.service_line_ids.filtered('in_use').filtered(
                lambda l: l.order_line_ids)
            service_added = analyse.service_line_ids.filtered('in_use').filtered(
                lambda l: l.invoice_line_ids and not l.order_line_ids)
            analyse.cout_service = sum(service_used.mapped('purchase_price_compute'))
            analyse.cout_service_additionnels = sum(service_added.mapped('purchase_price_compute'))
            analyse.cout_service_total = analyse.cout_service + analyse.cout_service_additionnels

            analyse.vente_service = sum(service_used.mapped('subtotal'))
            analyse.vente_service_additionnels = sum(service_added.mapped('subtotal'))
            analyse.vente_service_total = analyse.vente_service + analyse.vente_service_additionnels + sum(
                analyse.remise_ids.filtered(lambda r: r.active and r.affectation == 'service').mapped('subtotal'))

    @api.depends('product_line_ids.subtotal_compute', 'product_line_ids.purchase_price',
                 'service_line_ids.subtotal_compute', 'service_line_ids.purchase_price',
                 'remise_ids.affectation')
    def _compute_marge(self):
        for analyse in self:
            interventions = analyse.intervention_ids.filtered('in_use')
            product_line_filtered = analyse.product_line_ids.filtered('in_use')
            service_line_filtered = analyse.service_line_ids.filtered('in_use')
            cost = sum(product_line_filtered.mapped('purchase_price_compute'))
            sold = sum(product_line_filtered.mapped('subtotal_compute')) + sum(service_line_filtered.mapped('subtotal_compute')) + sum(analyse.remise_ids.filtered('active').mapped('subtotal'))
            cost_service = sum(service_line_filtered.mapped('purchase_price_compute'))
            analyse.cout_chantier = cost + cost_service
            analyse.vente_chantier = sold
            if sold != 0 and cost != 0:
                analyse.marge_brute = sold - cost
                analyse.marge_brute_pc = ((sold - cost) * 100 / sold)
                cost += cost_service
                marge_semi_nette = sold - cost - sum(interventions.mapped('cout_moyen_theorique'))
                analyse.marge_semi_nette = marge_semi_nette
                analyse.marge_semi_nette_pc = marge_semi_nette * 100 / sold
                marge_nette = sold - cost - sum(interventions.mapped('cout_theorique'))
                analyse.marge_nette = marge_nette
                analyse.marge_nette_pc = marge_nette * 100 / sold

    @api.multi
    def action_view_orders(self):
        action = self.env.ref('of_analyse_chantier.action_view_sale_order_analyse').read()[0]
        action['domain'] = [('id', 'in', self.order_ids._ids)]
        return action

    @api.multi
    def action_view_invoices(self):
        action = self.env.ref('of_analyse_chantier.action_view_account_invoice_analyse').read()[0]
        action['domain'] = [('id', 'in', self.invoice_ids._ids)]
        return action

    @api.multi
    def action_view_pickings(self):
        action = self.env.ref('of_analyse_chantier.action_view_stock_picking_analyse').read()[0]
        action['domain'] = [('id', 'in', self.picking_ids._ids)]
        return action

    @api.depends('order_ids', 'invoice_ids')
    def _compute_partner(self):
        for analyse in self:
            if analyse.order_ids:
                partner = analyse.order_ids.mapped('partner_id')
                if len(partner) > 1:
                    continue
                analyse.partner_id = partner
            elif analyse.invoice_ids:
                partner = analyse.invoice_ids.mapped('partner_id')
                if len(partner) > 1:
                    continue
                analyse.partner_id = partner

    @api.multi
    def recuperer_facture_liees(self):
        categ_acompte = self.env['ir.values'].get_default('sale.config.settings',
                                                          'of_deposit_product_categ_id_setting') or False
        invoices = self.order_ids.mapped('invoice_ids')
        if categ_acompte:
            for invoice in invoices:
                is_acompte = True
                for line in invoice.invoice_line_ids:
                    if line.product_id.categ_id.id != categ_acompte:
                        is_acompte = False
                        break
                if is_acompte:
                    invoices -= invoice
        invoices_to_add = [(4, invoice.id) for invoice in invoices if invoice not in self.invoice_ids]
        self.write({'invoice_ids': invoices_to_add})

    @api.multi
    def recuperer_commande_client_liees(self):
        orders = self.invoice_ids.mapped('invoice_line_ids').mapped('of_order_line_ids').mapped('order_id')
        orders_to_add = [(4, order.id) for order in orders if order not in self.order_ids]
        self.write({'order_ids': orders_to_add})

    @api.multi
    def recuperer_poses_liees(self):
        pass

    @api.multi
    def synchroniser(self):
        categ_acompte = self.env['ir.values'].get_default('sale.config.settings', 'of_deposit_product_categ_id_setting') or False
        categs_remise = self.env['ir.values'].get_default('sale.config.settings', 'of_discount_product_categ_ids_setting') or []
        order_lines = self.order_ids.mapped('order_line')
        invoices = self.order_ids.mapped('invoice_ids')
        pickings = self.order_ids.mapped('picking_ids')

        invoices += self.invoice_ids
        invoice_lines = invoices.mapped('invoice_line_ids')

        invoice_line_kit = invoice_lines.filtered('of_is_kit')
        order_line_kit = order_lines.filtered('of_is_kit')

        invoice_lines -= invoice_line_kit
        order_lines -= order_line_kit
        products = invoice_lines.mapped('product_id') + order_lines.mapped('product_id')
        self.invoice_ids = invoices
        self.picking_ids = pickings


        for product in products:
            if product.categ_id.id == categ_acompte:
                continue
            if product.categ_id.id in categs_remise:
                lines = self.remise_ids
            else:
                if product.type == 'service':
                    lines = self.service_line_ids
                else:
                    lines = self.product_line_ids
            analyse_line = lines.filtered(lambda al: al.product_id.id == product.id)
            if not analyse_line:
                if invoice_lines.filtered(lambda l: l.product_id.id == product.id):
                    analyse_line.create_line_from_invoice_lines(invoice_lines.filtered(lambda l: l.product_id.id == product.id), self)
                elif order_lines.filtered(lambda l: l.product_id.id == product.id):
                    analyse_line.create_line_from_order_lines(order_lines.filtered(lambda l: l.product_id.id == product.id), self)
            else:
                analyse_line.synchroniser()

        order_line_kit -= invoice_line_kit.mapped('of_order_line_ids')

        for line in invoice_line_kit:
            if line.kit_id:
                prods = line.kit_id.kit_line_ids.mapped('product_id')
                for product in prods:
                    if product.categ_id.id == categ_acompte:
                        continue
                    if product.categ_id.id in categs_remise:
                        lines = self.remise_ids
                    else:
                        if product.type == 'service':
                            lines = self.service_line_ids
                        else:
                            lines = self.product_line_ids
                    analyse_line = lines.filtered(lambda al: al.product_id.id == product.id)
                    if not analyse_line:
                        kit_lines = line.kit_id.kit_line_ids.filtered(lambda l: l.product_id.id == product.id)
                        analyse_line.create_line_from_invoice_kit_lines(kit_lines, self)
                    else:
                        analyse_line.synchroniser()

        for line in order_line_kit:
            if line.kit_id:
                prods = line.kit_id.kit_line_ids.mapped('product_id')
                for product in prods:
                    if product.categ_id.id == categ_acompte:
                        continue
                    if product.categ_id.id in categs_remise:
                        lines = self.remise_ids
                    else:
                        if product.type == 'service':
                            lines = self.service_line_ids
                        else:
                            lines = self.product_line_ids
                    analyse_line = lines.filtered(lambda al: al.product_id.id == product.id)
                    if not analyse_line:
                        kit_lines = line.kit_id.kit_line_ids.filtered(lambda l: l.product_id.id == product.id)
                        analyse_line.create_line_from_order_kit_lines(kit_lines, self)
                    else:
                        analyse_line.synchroniser()


        pack_operations = pickings.mapped('pack_operation_product_ids')
        order_lines |= invoice_lines.mapped('of_order_line_ids')
        for invoice_line in invoice_line_kit:
            order_line_kit |= invoice_line.mapped('of_order_line_ids')
        for order_line in order_lines:
            operations = order_line.mapped('procurement_ids')\
                                   .mapped('move_ids')\
                                   .mapped('linked_move_operation_ids')\
                                   .mapped('operation_id')
            for operation in operations:
                if operation in pack_operations:
                    pack_operations -= operation
        for invoice_line in invoice_line_kit:
            order_line_kit |= invoice_line.mapped('of_order_line_ids')
        for order_line in order_line_kit:
            operations = order_line.mapped('kit_id').mapped('kit_line_ids').mapped('procurement_ids') \
                                   .mapped('move_ids') \
                                   .mapped('linked_move_operation_ids') \
                                   .mapped('operation_id')
            for operation in operations:
                if operation in pack_operations:
                    pack_operations -= operation
        if pack_operations:
            for operation in pack_operations:
                product = operation.product_id
                if product.type == 'service':
                    lines = self.service_line_ids
                else:
                    lines = self.product_line_ids
                analyse_line = lines.filtered(lambda al: al.pack_operation_id.id == operation.id)
                if not analyse_line:
                    analyse_line.create_line_from_pack_operation(operation, self)
                else:
                    analyse_line.synchroniser()


    @api.model
    def create(self, vals):
        ret = super(OfAnalyseChantier, self).create(vals)
        ret.synchroniser()
        return ret

    @api.multi
    def write(self, vals):
        return super(OfAnalyseChantier, self).write(vals)

class SaleOrder(models.Model):
    _inherit = "sale.order"

    of_analyse_id = fields.Many2one('of.analyse.chantier', string="Analyse de chantier", copy=False)

    @api.multi
    def action_view_analyse_chantier(self):
        action = self.env.ref('of_analyse_chantier.action_sale_order_analyse_chantier').read()[0]
        action['res_id'] = self.of_analyse_id.id
        return action

    @api.multi
    def creer_analyse_chantier(self):
        if not self:
            return
        partner_id = self[0].partner_id.id
        for order in self:
            if order.partner_id.id != partner_id:
                raise UserWarning(u"Vous ne pouvez pas créer d'analyse avec "
                                  u"des bons de commandes ayant des clients différents.")
        analyse = self.env['of.analyse.chantier'].create({'order_ids': [(4, o.id) for o in self]})
        return analyse

    @api.multi
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        if self.env['ir.values'].get_default('sale.config.settings', 'of_create_analyse_auto'):
            self.sudo().creer_analyse_chantier()
        return res


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    of_analyse_id = fields.Many2one('of.analyse.chantier', string="Analyse de chantier", copy=False)


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    of_order_line_ids = fields.Many2many('sale.order.line', 'sale_order_line_invoice_rel', 'invoice_line_id', 'order_line_id', string='Order Lines', copy=False)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    of_cout_horaire = fields.Float(string=u"Coût horaires", default=0.0)

    @api.model
    def get_cout_horaire_moyen(self):
        employees = self.env['hr.employee'].search([('of_cout_horaire', '!=', 0)])
        return employees and sum(employees.mapped('of_cout_horaire')) / len(employees) or 0


class OfPlanningEquipe(models.Model):
    _inherit = "of.planning.equipe"

    @api.multi
    def cout_moyen_equipe(self):
        self.ensure_one()
        return len(self.employee_ids) * self.env['hr.employee'].get_cout_horaire_moyen()


class OfPlanningIntervention(models.Model):
    _inherit = 'of.planning.intervention'

    cout_theorique = fields.Float(string=u"Coût théorique", compute="_compute_cout_theorique")
    cout_equipe_heure = fields.Float(string=u"Coût de l'équipe", compute="_compute_cout_theorique")
    cout_moyen_equipe_heure = fields.Float(string=u"Coût moyen", compute="_compute_cout_theorique")
    cout_moyen_theorique = fields.Float(string=u"Coût moyen théorique", compute="_compute_cout_theorique")
    in_use = fields.Boolean(string="Inclure dans l'analyse", default=True)

    @api.depends('duree', 'employee_ids', 'in_use')
    def _compute_cout_theorique(self):
        for intervention in self:
            if intervention.in_use:
                intervention.cout_moyen_equipe_heure = intervention.employee_ids.get_cout_horaire_moyen() * len(intervention.employee_ids)
                intervention.cout_moyen_theorique = intervention.employee_ids.get_cout_horaire_moyen() * len(intervention.employee_ids) * intervention.duree
                intervention.cout_equipe_heure = sum(intervention.employee_ids.mapped('of_cout_horaire'))
                intervention.cout_theorique = sum(intervention.employee_ids.mapped('of_cout_horaire')) * intervention.duree

    @api.multi
    def toggle_use(self):
        self.in_use = not self.in_use


class StockPicking(models.Model):
    _inherit = "stock.picking"

    of_analyse_id = fields.Many2one('of.analyse.chantier', string="Analyse de chantier", copy=False)
