# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.model
    def _default_warehouse_id(self):
        company = self.env.user.company_id.id
        warehouse_ids = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
        return warehouse_ids

    of_boutique = fields.Boolean(string="Est une vente en boutique", default=False)
    of_procurement_group_id = fields.Many2one('procurement.group', 'Procurement Group', copy=False)
    of_picking_ids = fields.Many2many('stock.picking', compute='_compute_picking_ids')
    of_picking_count = fields.Integer(string="Bon de livraisons", compute='_compute_picking_ids')
    of_warehouse_id = fields.Many2one('stock.warehouse', string=u"Entrepôt", default=lambda s: s._default_warehouse_id())
    of_route_id = fields.Many2one('stock.location.route', string="Route")

    @api.multi
    @api.depends('of_procurement_group_id')
    def _compute_picking_ids(self):
        """
        Calcule le nombre de BL liés à la facture.
        :return:
        """
        for invoice in self:
            invoice.of_picking_ids = self.env['stock.picking'].search(
                    [('group_id', '=', invoice.of_procurement_group_id.id)]) if invoice.of_procurement_group_id else []
            invoice.of_picking_count = len(invoice.of_picking_ids)

    @api.multi
    def action_view_delivery(self):
        """
        Afficher les BL liés à la facture
        :return:
        """
        action = self.env.ref('stock.action_picking_tree_all').read()[0]

        pickings = self.mapped('of_picking_ids')
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = pickings.id
        return action

    def _prepare_procurement_group(self):
        return {
            'name': self.move_name,
            'partner_id': self.partner_shipping_id and self.partner_shipping_id.id or\
                          self.partner_id.id
        }

    @api.multi
    def action_invoice_open(self):
        """
        Surcharge de la fonction pour générer et valider un BL lors de vente en boutique
        :return:
        """
        res = super(AccountInvoice, self).action_invoice_open()
        if self.of_boutique:
            if not self.partner_id.property_stock_customer:
                raise UserError(u"""Votre client n'a pas d'emplacement lié.\n"""
                                u"""Veuillez vérifier dans la fiche partenaire, onglet 'Ventes & Achats' """
                                u"""le champ 'Emplacement Client'.""")
            transfer_obj = self.env['stock.immediate.transfer']
            procs = self.invoice_line_ids._action_procurement_create()
            moves = procs.mapped('move_ids')
            pickings = moves.mapped('picking_id')
            pickings.force_assign()
            for picking in pickings:
                new_transfer = transfer_obj.create({'pick_id': picking.id})
                new_transfer.process()
        return res

    @api.model
    def create(self, vals):
        if vals.get('of_boutique'):
            partner = self.env['res.partner'].browse(vals['partner_id'])
            vals.update({'name': 'Vente boutique - %s' % partner.name})
        return super(AccountInvoice, self).create(vals)


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    of_route_id = fields.Many2one('stock.location.route', string="Route")

    @api.multi
    def _prepare_invoice_line_procurement(self, group_id=False):
        """
        :param group_id: Groupe de procurement.order
        :return: dictionnaire de valeur pour créer les procurement.order
        """
        self.ensure_one()
        warehouse_id = self.invoice_id.of_warehouse_id
        return {
            'name'           : self.name,
            'origin'         : self.invoice_id.name,
            'date_planned'   : fields.Datetime.now(),
            'product_id'     : self.product_id.id,
            'product_qty'    : self.quantity,
            'product_uom'    : self.uom_id.id,
            'company_id'     : self.invoice_id.company_id.id,
            'group_id'       : group_id,
            'location_id'    : self.invoice_id.partner_shipping_id and\
                               self.invoice_id.partner_shipping_id.property_stock_customer.id or\
                               self.invoice_id.partner_id.property_stock_customer.id,
            'route_ids'      : self.of_route_id and [(4, self.of_route_id.id)] or [],
            'warehouse_id'   : warehouse_id and warehouse_id.id or False,
            'partner_dest_id': self.invoice_id.partner_id.id,
            # 'sale_line_id'   : self.id,
            }

    @api.multi
    def _action_procurement_create(self):
        """
        Basé sur le code du module sale pour la création d'approvisionnement lors de la validation de devis
        Créer les procurement.order des lignes de la facture ce qui va générer un BL
        """
        new_procs = self.env['procurement.order']  # Empty recordset
        for line in self:
            if line.invoice_id.state != 'open' or not line.product_id._need_procurement():
                continue
            if not line.invoice_id.of_procurement_group_id:
                vals = line.invoice_id._prepare_procurement_group()
                line.invoice_id.of_procurement_group_id = self.env["procurement.group"].create(vals)

            vals = line._prepare_invoice_line_procurement(group_id=line.invoice_id.of_procurement_group_id.id)
            vals['product_qty'] = line.quantity
            new_proc = self.env["procurement.order"].with_context(procurement_autorun_defer=True).create(vals)
            new_proc.message_post_with_view('mail.message_origin_link',
                values={'self': new_proc, 'origin': line.invoice_id},
                subtype_id=self.env.ref('mail.mt_note').id)
            new_procs += new_proc
        new_procs.run()
        return new_procs
