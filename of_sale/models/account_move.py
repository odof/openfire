# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

# import json  TODO: Uncomment me when `of_account` module is migrated

from odoo import Command, api, fields, models

# from odoo.tools import float_compare  TODO: Uncomment me when `of_account` module is migrated


class AccountMove(models.Model):
    _inherit = 'account.move'

    of_is_locked = fields.Boolean(compute='_compute_of_is_locked', string="Locked")
    of_sale_order_ids = fields.Many2many(
        comodel_name='sale.order', compute='_compute_of_sale_order_ids', string="Sale orders"
    )
    of_waiting_delivery = fields.Boolean(compute='_compute_of_picking_ids', string="Delivery on hold")
    of_picking_ids = fields.Many2many(
        comodel_name='stock.picking', compute='_compute_of_picking_ids', string="Deliveries"
    )
    of_picking_count = fields.Integer(compute='_compute_of_picking_ids', string="Nbr of deliveries")
    # TODO: Uncomment me and continue the migration when `of_account` module is migrated
    # of_residual = fields.Monetary(
    #     string="Sum of the unpaid amount of the deposit invoices and the final invoice",
    #     compute='_compute_of_residual',
    # )
    # of_residual_equal = fields.Boolean(compute='_compute_of_residual', string="Residual equal")
    # End of TODO: Migrate me when `of_account` module is migrated
    of_internal_followup = fields.Char(string="Internal follow-up")
    of_price_printing = fields.Selection(
        selection='_get_selection_of_price_printing',
        string="Price printing",
        default='order_line',
        required=True,
    )

    def _get_selection_of_price_printing(self):
        """Return the same selection as in sale.order.of_price_printing"""
        return self.env['sale.order'].fields_get(allfields=['of_price_printing'])['of_price_printing']['selection']

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    @api.depends('invoice_line_ids', 'invoice_line_ids.of_is_locked')
    def _compute_of_is_locked(self):
        for move in self:
            of_is_locked = False
            if move.invoice_line_ids == move.invoice_line_ids.filtered(lambda aml: aml.of_is_locked):
                of_is_locked = True
            move.of_is_locked = of_is_locked

    @api.depends('invoice_line_ids')
    def _compute_of_sale_order_ids(self):
        for move in self:
            move.of_sale_order_ids = move.invoice_line_ids.mapped('sale_line_ids').mapped('order_id')

    @api.depends(
        'invoice_line_ids',
        'invoice_line_ids.sale_line_ids',
        'invoice_line_ids.sale_line_ids.order_id',
        'invoice_line_ids.sale_line_ids.order_id.picking_ids',
    )
    def _compute_of_picking_ids(self):
        """Compute the number of pickings linked to the invoice and the pickings themselves"""
        for move in self:
            of_waiting_delivery = False
            of_picking_ids = False
            of_picking_count = False
            if pickings := move.of_sale_order_ids.mapped('picking_ids'):
                of_waiting_delivery = (
                    pickings.filtered(lambda p: p.state not in ['draft', 'cancel', 'done']) and True or False
                )
                of_picking_ids = pickings
                of_picking_count = len(pickings)
            move.of_waiting_delivery = of_waiting_delivery
            move.of_picking_ids = of_picking_ids
            move.of_picking_count = of_picking_count

    # TODO: Uncomment me and continue the migration when `of_account` module is migrated
    # @api.depends('invoice_line_ids')
    # def _compute_of_residual(self):
    #     group_paiements = self.env['of.invoice.report.total.group'].get_group_paiements()
    #     if not group_paiements.invoice:
    #         # Si le groupe des paiements est désactivé on ne gère pas les acomptes
    #         group_paiements = group_paiements.browse()
    #     products = group_paiements.product_ids
    #     if group_paiements.categ_ids:
    #         products |= self.env['product.product'].search([('categ_id', 'in', group_paiements.categ_ids.ids)])
    #     if not products:
    #         for move in self:
    #             move.of_residual = move.residual
    #             move.of_residual_equal = True
    #         return
    #     for move in self:
    #         lines = move.invoice_line_ids.filtered(lambda l: l.product_id in products)
    #         if not lines:
    #             move.of_residual = move.residual
    #             move.of_residual_equal = True
    #             continue
    #         order_lines = lines.mapped('sale_line_ids')
    #         moves = move | order_lines.mapped('invoice_lines').mapped('move_id')
    #         move.of_residual = sum(moves.mapped('residual'))
    #         move.of_residual_equal = move.state == 'draft' or float_compare(move.of_residual, move.residual, 2) == 0
    # End of TODO: Migrate me and continue the migration when `of_account` module is migrated

    # -------------------------------------------------------------------------
    # Onchange methods
    # -------------------------------------------------------------------------

    @api.onchange('partner_id')
    def _onchange_partner_id_warning(self):
        partner = self.partner_id

        # If partner has no warning, check its parents
        # invoice_warn is shared between different objects
        if not partner.of_is_account_warn and partner.parent_id:
            partner = partner.parent_id

        if partner.of_is_account_warn and partner.invoice_warn != 'no-message':
            return super()._onchange_partner_id_warning()
        return

    # -------------------------------------------------------------------------
    # Action methods
    # -------------------------------------------------------------------------

    def action_button_view_delivery(self):
        """Open deliveries linked to the invoice. If there is only one delivery, open it in form view, otherwise open
        the list view of the deliveries."""
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_picking_tree_all")
        pickings = self.of_picking_ids
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            form_view = [(self.env.ref('stock.view_picking_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = pickings.id
        picking_id = pickings and pickings[0] or False
        action['context'] = dict(
            self._context,
            default_partner_id=self.partner_id.id,
            default_picking_type_id=picking_id.picking_type_id.id,
            default_origin=self.name,
            default_group_id=picking_id.group_id.id,
        )
        return action

    def action_button_validate_pickings(self):
        """Force the availability of the products in the pickings linked to the invoice and validate them"""
        transfer_obj = self.env['stock.immediate.transfer']
        for move in self.filtered(lambda i: not i.of_is_locked):
            pickings = move.of_picking_ids
            pickings.action_clear_quantities_to_zero()
            pickings.action_assign()
            for picking in pickings:
                new_transfer = transfer_obj.create(
                    {
                        'pick_ids': [Command.link(picking.id)],
                        'immediate_transfer_line_ids': [
                            Command.create({'to_immediate': True, 'picking_id': picking.id})
                        ],
                    }
                )
                new_transfer.with_context(button_validate_picking_ids=[picking.id]).process()
        self._compute_of_picking_ids()

    def action_post(self):
        result = super().action_post()
        if self.env['ir.config_parameter'].sudo().get_param('of.sale.of_validate_pickings_on_move') == 'validate':
            self.action_button_validate_pickings()
        return result

    # -------------------------------------------------------------------------
    # Reporting methods
    # -------------------------------------------------------------------------

    def pdf_get_color_bg_section(self):
        return (
            self.env['ir.config_parameter'].sudo().get_param('of.sale.report.account.move.of_color_bg_section')
            or "#f0f0f0"
        )

    def pdf_get_color_font_section(self):
        return (
            self.env['ir.config_parameter'].sudo().get_param('of.sale.report.account.move.of_color_font_section')
            or "#000000"
        )

    # TODO: Uncomment me and continue the migration when `of_account` module is migrated
    # def _report_of_get_linked_invoices(self):
    #     """[IMPRESSION]
    #     Retourne les factures liées à la facture courante.
    #     Les factures liées sont celles dont une ligne est liée à la même ligne de commande qu'une ligne de lines.
    #     Toute facture liée à une facture liée est également retournée.
    #     """
    #     move_obj = self.env['account.move']
    #     self.ensure_one()
    #     if self.move_type != 'out_invoice':
    #         return self

    #     payments_groups = self.env['of.invoice.report.total.group'].get_group_paiements()
    #     if not (payments_groups and payments_groups.invoice):
    #         # Le groupe des paiements n'est pas coniguré pour les factures.
    #         return self

    #     payments_groups_lines = payments_groups.filter_lines(self.invoice_line_ids, self)
    #     if payments_groups_lines is False:
    #         # Aucune ligne de la facture n'est à considérer comme un paiement.
    #         return self

    #     moves = self
    #     to_check = (
    #         payments_groups_lines.mapped('sale_line_ids')
    #         .mapped('invoice_lines')
    #         .mapped('move_id')
    #         .filtered(lambda i: i.state != 'cancel')
    #     ) - self
    #     while to_check:
    #         moves |= to_check
    #         to_check = (
    #             to_check.mapped('invoice_line_ids')
    #             .mapped('sale_line_ids')
    #             .mapped('invoice_lines')
    #             .mapped('move_id')
    #             .filtered(lambda i: i.state != 'cancel')
    #         ) - moves

    #     refunds = moves.filtered(lambda mov: mov.move_type != self.move_type)
    #     moves -= refunds
    #     for refund in refunds:
    #         # On fait abstraction des factures annulées par des avoirs
    #         move_ids = refund.payment_move_line_ids.mapped('move_id')
    #         if len(move_ids) == 1:
    #             if move := moves.filtered(
    #                 lambda mov: mov.move_id == move_ids and mov.amount_total == refund.amount_total
    #             ):
    #                 if move == self:
    #                     # La facture en cours est annulée par un avoir
    #                     return self
    #                 moves -= move

    #     # On ne garde que les factures dont toutes les lignes sont contrebalancées
    #     order_lines = moves.mapped('invoice_line_ids').mapped('sale_line_ids')
    #     while order_lines:
    #         moves_to_remove = move_obj
    #         for order_line in order_lines:
    #             movs = order_line.invoice_lines.mapped('move_id').filtered(lambda mov: mov in moves)
    #             if len(movs) == 1 and movs != self:
    #                 moves_to_remove |= movs
    #         moves -= moves_to_remove
    #         order_lines = moves_to_remove.mapped('invoice_line_ids').mapped('sale_line_ids')

    #     # Tri dans l'ordre
    #     moves = move_obj.search([('id', 'in', moves.ids)])
    #     return moves
    # End of TODO: Uncomment me and continue the migration when `of_account` module is migrated

    # TODO: Uncomment me and continue the migration when `of_account` module is migrated
    # def _report_of_get_printable_payments(self):
    #     """[IMPRESSION]
    #     Renvoie les lignes à afficher.
    #     """
    #     account_move_line_obj = self.env['account.move.line']

    #     # Retour de tous les paiements des factures
    #     # On distingue les paiements de la facture principale de ceux des factures liées
    #     result_dict = {}
    #     for move in self:
    #         payment_widget_vals = move.invoice_payments_widget
    #         if not payment_widget_vals:
    #             continue
    #         for payment in payment_widget_vals.get('content', []):
    #             # Les paiements sont classés dans l'ordre chronologique
    #             sort_key = (payment['date'], move.invoice_date, move.name, payment['payment_id'])
    #             move_line = account_move_line_obj.browse(payment['payment_id'])
    #             name = self._of_get_payment_display(move_line)
    #             result_dict[sort_key] = (name, payment['amount'])
    #     return [result_dict[key] for key in sorted(result_dict)]
    # End of TODO: Uncomment me and continue the migration when `of_account` module is migrated

    # TODO: Uncomment me and continue the migration when `of_account` module is migrated
    # def _report_of_get_recap_taxes(self, moves):
    #     """[IMPRESSION]
    #     Retourne la liste des taxes à afficher dans le récapitulatif de la facture pdf.
    #     """
    #     self.ensure_one()
    #     tax_vals = []
    #     taxes = {}
    #     round_curr = self.currency_id.round
    #     move_type = self.move_type
    #     for move in moves:
    #         sign = move.move_type == move_type or -1
    #         for inv_tax in move.tax_line_ids:
    #             tax = inv_tax.tax_id
    #             if tax in taxes:
    #                 vals = taxes[tax]
    #                 vals[1] += inv_tax.base * sign
    #                 vals[2] += inv_tax.amount * sign
    #             else:
    #                 vals = [tax.description, inv_tax.base * sign, inv_tax.amount * sign]
    #                 tax_vals.append(vals)
    #                 taxes[tax] = vals
    #     for vals in tax_vals:
    #         vals[1] = round_curr(vals[1])
    #         vals[2] = round_curr(vals[2])
    #     return [vals for vals in tax_vals if vals[1]]
    # End of TODO: Uncomment me and continue the migration when `of_account` module is migrated

    # TODO: Uncomment me and continue the migration when `of_account` module is migrated
    # def _report_of_get_printable_data(self):
    #     result = super()._report_of_get_printable_data()
    #     lines_to_report = self._get_order_lines_to_report()
    #     report_lines = result['lines']
    #     report_pages = []
    #     for page_full in report_pages_full:  # FIXME: report_pages_full is not defined, old `order_lines_layouted()`
    #         page = []
    #         for group in page_full:
    #             lines = [line for line in group['lines'] if line in report_lines]
    #             if lines:
    #                 group['lines'] = lines
    #                 page.append(group)
    #         if page:
    #             report_pages.append(page)
    #     result['lines_layouted'] = report_pages
    #     return result
    # End of TODO: Uncomment me and continue the migration when `of_account` module is migrated
