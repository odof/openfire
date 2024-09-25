# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, float_compare

from odoo.addons.of_utils.models.misc import get_selection_label


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'of.form.readonly']

    def _default_of_price_printing(self):
        return 'order_line'

    # Dates
    of_date_order = fields.Datetime(string="Forced confirmation date", readonly=True, copy=False)

    # Printing
    of_price_printing = fields.Selection(
        selection='_get_selection_of_price_printing',
        string="Price printing",
        default=lambda self: self._default_of_price_printing(),
        required=True,
    )
    of_printing_apply_on_move = fields.Boolean(string="Apply to invoices", default=True)

    # Pricing
    of_total_cost = fields.Monetary(compute='_compute_of_total_cost', string="Total cost price")

    # Invoicing : Invoice policy, Invoice date, Estimated invoicing date, etc.
    of_fully_invoicable = fields.Boolean(
        string="Fully invoicable", compute='_compute_of_fully_invoicable', search='_search_of_fully_invoicable'
    )
    of_force_invoice_status = fields.Selection(
        selection=[('invoiced', 'Fully Invoiced'), ('no', 'Nothing to Invoice')],
        string="Force Invoice Status",
        tracking=True,
        help="Allows you to force the billing status of the order."
        "Useful for invoiced orders that refuse to change status (e.g. a line has been deleted in the invoice).",
        copy=False,
    )
    of_invoice_policy = fields.Selection(
        selection=[('order', "Ordered quantities"), ('delivery', "Delivered quantities")],
        string="Invoicing policy",
        compute='_compute_of_invoice_policy',
        store=True,
        readonly=False,
    )
    of_fixed_invoice_date = fields.Date(string="Fixed invoice date")
    of_estimated_invoicing_date = fields.Date(
        string="Anticipated invoicing date",
        compute='_compute_of_estimated_invoicing_date',
        inverse='_inverse_of_estimated_invoicing_date',
        store=True,
        compute_sudo=True,
    )

    # Delivery
    of_is_delivered = fields.Boolean(string="Is the order delivered ?", compute='_compute_of_is_delivered', store=True)

    # Customer, project, interventions informations
    client_order_ref = fields.Char(compute='_compute_client_order_ref', readonly=False, store=True)
    of_customer_category_ids = fields.Many2many(
        comodel_name='res.partner.category', related='partner_id.category_id', string="Customer tags"
    )
    of_customer_notes = fields.Html(related='partner_id.comment', string="Customer notes", readonly=True)
    of_partner_phone = fields.Char(related='partner_id.phone', string="Customer's phone", readonly=True)
    of_partner_mobile = fields.Char(related='partner_id.mobile', string="Customer's mobile", readonly=True)
    of_partner_email = fields.Char(related='partner_id.email', string="Customer's e-mail", readonly=True)

    # Other helper fields
    of_allow_quote_addition = fields.Boolean(
        string="Allows you to add additional quotes", compute='_compute_of_allow_quote_addition'
    )
    of_customer_view = fields.Boolean(string="Customer/Vendor view")

    def _get_selection_of_price_printing(self):
        return [
            ('order_line', "Price per order line"),
        ]

    # --------------------------------------------------------------------------
    # Compute methods
    # --------------------------------------------------------------------------

    def _compute_fiscal_position_id(self):
        cache = {order: order.fiscal_position_id for order in self}
        super()._compute_fiscal_position_id()
        for order in self.filtered(lambda o: not o.fiscal_position_id and o.fiscal_position_id != cache[o]):
            if cache[order]:
                order.fiscal_position_id = cache[order]
                continue

    def _compute_payment_term_id(self):
        cache = {order: (order.company_id, order.payment_term_id) for order in self}
        super()._compute_payment_term_id()
        # Ensure that the company hasn't changed since the last computation (which is company-dependent)
        # to avoid setting a payment term that is not valid for the new company.
        for order in self.filtered(lambda o: not o.payment_term_id and o.company_id == cache[o][0] and cache[o][1]):
            order.payment_term_id = cache[order][1]

    @api.depends('partner_id')
    def _compute_client_order_ref(self):
        for order in self:
            if self.partner_id:
                ref = self.partner_id.ref
                if not ref and self.partner_id.parent_id:
                    ref = self.partner_id.parent_id.ref
                order.client_order_ref = ref

    @api.depends('partner_id')
    def _compute_partner_invoice_id(self):
        super()._compute_partner_invoice_id()
        for order in self.filtered(lambda o: not o.partner_invoice_id.of_default_address):
            if default_invoice_address := order.partner_id.child_ids.filtered(
                lambda child: child.type == 'invoice' and child.of_default_address
            ):
                order.partner_invoice_id = default_invoice_address[0]  # take arbitrarily the first one

    @api.depends('partner_id')
    def _compute_partner_shipping_id(self):
        super()._compute_partner_shipping_id()
        for order in self.filtered(lambda o: not o.partner_shipping_id.of_default_address):
            if default_shipping_address := order.partner_id.child_ids.filtered(
                lambda child: child.type == 'delivery' and child.of_default_address
            ):
                order.partner_shipping_id = default_shipping_address[0]  # take arbitrarily the first one

    @api.depends('company_id')
    def _compute_of_allow_quote_addition(self):
        of_allow_quote_addition = self.env['ir.config_parameter'].sudo().get_param('of.sale.of_allow_quote_addition')
        for order in self:
            order.of_allow_quote_addition = of_allow_quote_addition

    def _search_of_fully_invoicable(self, operator, value):
        # Récupération des bons de commande non entièrement livrés
        self._cr.execute(
            "SELECT DISTINCT order_id FROM sale_order_line WHERE qty_to_invoice + qty_invoiced < product_uom_qty"
        )
        order_ids = self._cr.fetchall()
        order_ids = list(map(lambda x: x[0], order_ids)) if order_ids else []
        domain = [
            '&',
            '&',
            ('of_force_invoice_status', 'not in', ('invoiced', 'no')),
            ('state', 'in', ('sale', 'done')),
            ('order_line.qty_to_invoice', '>', 0),
        ]
        if order_ids:
            domain = ['&'] + domain + [('id', 'not in', order_ids)]
        return domain

    @api.depends('state', 'order_line', 'order_line.qty_to_invoice', 'order_line.product_uom_qty')
    def _compute_of_fully_invoicable(self):
        for order in self:
            if order.state not in ('sale', 'done') or order.of_force_invoice_status in ('invoiced', 'no'):
                order.of_fully_invoicable = False
                continue
            for line in order.order_line:
                if line.qty_to_invoice + line.qty_invoiced < line.product_uom_qty:
                    order.of_fully_invoicable = False
                    break
            else:
                order.of_fully_invoicable = True

    @api.depends('margin', 'amount_untaxed')
    def _compute_of_total_cost(self):
        for order in self:
            order.of_total_cost = order.amount_untaxed - order.margin

    @api.depends('partner_id')
    def _compute_of_invoice_policy(self):
        for order in self:
            if order.partner_id:
                order.of_invoice_policy = order.partner_id.of_invoice_policy

    @api.depends(
        'of_fixed_invoice_date',
        'of_invoice_policy',
        'order_line',
        'order_line.of_estimated_invoicing_date',
        'order_line.move_ids',
        'order_line.move_ids.picking_id.scheduled_date',
    )
    def _compute_of_estimated_invoicing_date(self):
        for order in self:
            if order.of_fixed_invoice_date:
                order.of_estimated_invoicing_date = order.of_fixed_invoice_date
            elif order.of_invoice_policy == 'order':
                order.of_estimated_invoicing_date = order.of_fixed_invoice_date
            elif order.of_invoice_policy == 'delivery':
                if pickings := (
                    order.order_line.mapped('move_ids')
                    .mapped('picking_id')
                    .filtered(lambda p: p.state != 'cancel')
                    .sorted('scheduled_date')
                ):
                    order.of_estimated_invoicing_date = (
                        fields.Date.to_date(to_process_pickings[0].scheduled_date)
                        if (to_process_pickings := pickings.filtered(lambda p: p.state != 'done'))
                        else fields.Date.to_date(pickings[-1].scheduled_date)
                    )

    def _inverse_of_estimated_invoicing_date(self):
        for order in self:
            order.of_fixed_invoice_date = order.of_estimated_invoicing_date

    @api.depends('order_line', 'order_line.qty_delivered', 'order_line.product_uom_qty')
    def _compute_of_is_delivered(self):
        for order in self:
            for line in order.order_line:
                if float_compare(line.qty_delivered, line.product_uom_qty, 2) < 0:
                    order.of_is_delivered = False
                    break
            else:
                order.of_is_delivered = True

    # --------------------------------------------------------------------------
    # Onchange methods
    # --------------------------------------------------------------------------

    @api.onchange('partner_id')
    def _onchange_partner_id_warning(self):
        if not self.partner_id:
            return
        partner = self.partner_id

        # If partner has no warning, check its parents
        # invoice_warn is shared between different objects
        if not partner.of_is_sale_warn and partner.parent_id:
            partner = partner.parent_id

        if partner.of_is_sale_warn and partner.invoice_warn != 'no-message':
            return super()._onchange_partner_id_warning()
        return

    # --------------------------------------------------------------------------
    # ORM methods
    # --------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if self.env['ir.config_parameter'].sudo().get_param('of.sale.of_sale_mail_subtype_subscription'):
            if mail_subtype := self.env.ref('of_sale.mt_of_sale_mail_subscription', raise_if_not_found=False):
                # Subscribe the followers of the mail subtype to the new records
                records.message_subscribe(partner_ids=records.mapped('partner_id')._ids, subtype_ids=[mail_subtype.id])
        return records

    def write(self, vals):
        subtype_icp = self.env['ir.config_parameter'].sudo().get_param('of.sale.of_sale_mail_subtype_subscription')
        if subtype_icp:
            mail_subtype = self.env.ref('of_sale.mt_of_sale_mail_subscription', raise_if_not_found=False)
            old_partner_ids = mail_subtype and vals.get('partner_id') and self.mapped('partner_id').ids or []
        res = super().write(vals)
        if subtype_icp and (mail_subtype and vals.get('partner_id')):
            # Subscribe the new partner to the mail subtype
            self.message_subscribe(partner_ids=[vals['partner_id']], subtype_ids=[mail_subtype.id])
            message_followers = self.mapped('message_follower_ids')
            # Unsubscribe the old partners from the mail subtype
            message_followers.filtered(lambda r: r.partner_id.id in old_partner_ids).write(
                {'subtype_ids': [Command.unlink(mail_subtype.id)]}
            )
        return res

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        if self.env.user.has_group('of_sale.of_group_restrict_form_sale_order_modification') and view_type == 'form':
            self = self.with_context(form_readonly="[('state', '=', 'sale')]")
        return super()._get_view(view_id=view_id, view_type=view_type, **options)

    # --------------------------------------------------------------------------
    # Action methods
    # --------------------------------------------------------------------------

    def action_quotation_send(self):
        action = super().action_quotation_send()
        if self.env['ir.config_parameter'].sudo().get_param('of.sale.of_sale_mail_subtype_subscription'):
            if mail_subtype := self.env.ref('of_sale.mt_of_sale_mail_subscription', raise_if_not_found=False):
                action['context'].update({'default_subtype_id': mail_subtype.id})
        return action

    def action_verification_confirm(self):
        """
        Allows you to do the verification before starting the order confirmation.
        As there is no raise, if you want a check that blocks the confirmation, you have to do it outside
        action_confirm, otherwise some overloads that would be passed before/after will still be performed
        """
        action = False
        for order in self:
            action, need_interruption = self.env['of.sale.order.verification'].do_verification(order)
            if need_interruption:
                return action
        return action if need_interruption else self.action_confirm()

    def action_button_add_quote(self):
        self.ensure_one()
        if self.state not in self._get_valid_states_to_add_quote():
            raise UserError("You cannot add a complementary quote to a non-validated order.")

        wizard = self.env['of.sale.order.add.quote.wizard'].create(
            {
                'order_id': self.id,
            }
        )

        return {
            'type': 'ir.actions.act_window',
            'name': _("Add a complementary quote"),
            'view_mode': 'form',
            'res_model': 'of.sale.order.add.quote.wizard',
            'res_id': wizard.id,
            'target': 'new',
        }

    def action_button_toggle_view_mode(self):
        """Allows you to switch between the vendor/customer view"""
        for record in self:
            record.of_customer_view = not record.of_customer_view

    def action_button_sale_confirmation(self):
        self.ensure_one()
        context = self._context.copy()
        context['default_order_id'] = self.id
        context['default_confirmation_date'] = self.of_date_order or fields.Datetime.now()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Confirm sale"),
            'view_mode': 'form',
            'res_model': 'of.sale.order.confirmation',
            'res_id': False,
            'target': 'new',
            'context': context,
        }

    # --------------------------------------------------------------------------
    # Business logic methods
    # --------------------------------------------------------------------------

    @api.depends('order_line.invoice_lines', 'of_force_invoice_status')
    def _get_invoiced(self):
        super()._get_invoiced()
        for order in self.filtered(lambda o: o.of_force_invoice_status):
            order.invoice_status = order.of_force_invoice_status

    def _prepare_invoice(self):
        values = super()._prepare_invoice()  # <- self.ensure_one()
        if self.of_printing_apply_on_move:
            values['of_price_printing'] = self.of_price_printing
        if self.env['ir.config_parameter'].sudo().get_param(
            'of.sale.of_stop_payment_term_propagation'
        ) and not self._context.get('of_down_payment_final_invoice'):
            values['invoice_payment_term_id'] = False
        if self._context.get('of_down_payment_final_invoice'):
            if (
                balance_invoice_payment_term_id := self.payment_term_id
                and self.payment_term_id.of_balance_invoice_payment_term_id
            ):
                values.update({'invoice_payment_term_id': balance_invoice_payment_term_id.id})
        return values

    def name_get(self):
        if not self._context.get('sale_extended_name_display'):
            return super().name_get()
        result = []
        date_format = '%d/%m/%Y' if self.env.user.lang == 'fr_FR' else DEFAULT_SERVER_DATE_FORMAT
        for order in self:
            date_order = fields.Date.from_string(order.date_order).strftime(date_format)
            order_state = get_selection_label(self, order._name, 'state', order.state)
            result.append((order.id, f"{order.name} - {order_state} - {date_order}"))
        return result

    def _create_invoices(self, grouped=False, final=False, date=None):
        # The default value 'default_grouping' is equivalent to `grouped == False`, it will group by :
        # company, partner_id, currency_id). See `sale.order._get_invoice_grouping_keys()` for more information.
        grouped = (
            self.env['ir.config_parameter'].sudo().get_param('of.sale.of_grouped_invoicing', 'default_grouping')
            != 'default_grouping'
        )
        moves = super()._create_invoices(grouped=grouped, final=final, date=date)
        for move in moves:
            if len(move.invoice_line_ids.mapped('sale_line_ids').mapped('order_id')) > 1:
                for line in move.invoice_line_ids:
                    order_line = line.sale_line_ids[:1]
                    order_ref = order_line.order_id.client_order_ref or False
                    line.write(
                        {
                            'name': "%s%s%s%s"
                            % (
                                # We add the order reference to the invoice line name
                                # (for example: "SO1234\nLine name" or "SO1234 Order ref\nLine name")
                                order_line.order_id.name,
                                f" {order_ref}" if order_ref else '',
                                "\n" if order_line.order_id.name or order_ref else '',
                                line.name,
                            ),
                            'of_order_id': order_line.order_id.id,
                        }
                    )
        return moves

    def _prepare_confirmation_values(self):
        values = super()._prepare_confirmation_values()
        if self.env['ir.config_parameter'].sudo().get_param('of.sale.of_sale_confirmation_date_mode') == 'manual':
            values['date_order'] = self.of_date_order
        return values

    def _get_valid_states_to_add_quote(self):
        return ['sale', 'done']

    def copy_data(self, default=None):
        """By default, the opportunity is copied when the sale order is copied (attribute copy=True).
        TODO: Move this feature in of_sale_crm when the module will be migrated to v16.
        """
        data_list = super().copy_data(default)
        for order, data in zip(self, data_list):
            if self.env['ir.config_parameter'].sudo().get_param('of.sale.of_copy_opportunity_with_sale_order'):
                data['opportunity_id'] = order.opportunity_id.id
            else:
                data['opportunity_id'] = False
        return data_list
