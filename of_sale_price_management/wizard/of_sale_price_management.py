# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, format_amount


class OFPriceManagementWizard(models.TransientModel):
    _name = 'of.sale.price.management.wizard'
    _description = "Price management wizard"

    def _get_selection_discount_type(self):
        selection = [
            ('total_target_amnt_tax_incl', _("Total target amount incl. VAT")),
            ('amount_tax_incl', _("Amount incl. VAT to be deducted")),
            ('total_target_amnt_tax_excl', _("Total target amount excl. VAT")),
            ('amount_tax_excl', _("Amount excl. VAT to be deducted")),
            ('percentage', _("% Overall discount")),
        ]
        if self.user_has_groups('of_sale_margin.of_group_sale_margin_manager'):
            selection.append(('margin_percent', _("% Margin")))
        selection.append(('restore', _("Restore at store price")))
        return selection

    order_id = fields.Many2one(comodel_name='sale.order', string="Quotation/Order", required=True, ondelete='cascade')
    discount_mode = fields.Selection(
        selection=[
            ('line', "Apply price management to lines"),
            ('total', "Apply price management to totals"),
        ],
        string="Discount mode",
        required=True,
        default='line',
    )
    discount_product_id = fields.Many2one(comodel_name='product.product', string="Discount item")
    discount_type = fields.Selection(
        selection='_get_selection_discount_type',
        default='total_target_amnt_tax_incl',
        string="Calculation mode",
        help="Determines how the discount is calculated on the selected lines of the estimate",
    )
    line_ids = fields.One2many(
        comodel_name='of.sale.price.management.wizard.line', inverse_name='wizard_id', string="Impacted lines"
    )
    value = fields.Float(string="Value", digits='Sale Price')
    initial_margin = fields.Monetary(string="Initial margin", related='order_id.margin', related_sudo=False)
    initial_margin_percent = fields.Float(
        string="Initial margin %", related='order_id.margin_percent', related_sudo=False
    )
    init_total_amount_tax_incl = fields.Monetary(
        string="Initial total amount incl. VAT", related='order_id.amount_total', readonly=True
    )
    init_total_amount_tax_excl = fields.Monetary(
        string="Initial total amount excl. VAT", related='order_id.amount_untaxed', readonly=True
    )
    currency_id = fields.Many2one(related='order_id.currency_id')
    simulated_margin = fields.Monetary(string="Simulated margin", compute='_compute_simulated_amounts')
    simulated_margin_percent = fields.Float(string="Simulated margin %", compute='_compute_simulated_amounts')
    total_amount_sim_tax_incl = fields.Monetary(
        string="Total simulated incl. VAT", compute='_compute_simulated_amounts'
    )
    total_amount_sim_tax_excl = fields.Monetary(
        string="Total simulated excl. VAT", compute='_compute_simulated_amounts'
    )
    total_simulated_cost_tax_excl = fields.Monetary(
        string="Total simulated cost excl. VAT", compute='_compute_simulated_amounts'
    )
    display_discount = fields.Boolean(
        string="Display in notes",
        help="Displays the amount of discount made in the quote/order notes.",
    )
    rounding_mode = fields.Selection(
        [
            ('no_rounding', "No rounding"),
            ('total_excluded', "Rounding on amount excl. VAT"),
            ('total_included', "Rounding on amount incl. VAT"),
        ],
        string="Rounding by line",
        required=True,
        default='no_rounding',
    )

    rounding_precision = fields.Selection(
        [
            ('-1', "Round up to the nearest €10"),
            ('0', "Round to the nearest euro"),
            ('1', "Round to the nearest 10 cents"),
        ],
        string=u"Rounding precision",
        default='0',
    )
    calculation_basis = fields.Selection(
        selection=[
            ('price', "Sale price"),
            ('cost', "Cost"),
        ],
        default='price',
        required=True,
        string="Calculation basis",
    )
    customer_view = fields.Boolean(string="Customer/Vendor view")

    @api.depends(
        'line_ids.sim_total_price_tax_incl', 'line_ids.sim_total_price_tax_excl', 'line_ids.sim_total_cost_tax_excl'
    )
    def _compute_simulated_amounts(self):
        for wizard in self:
            lines = wizard.line_ids
            total_purchase = sum(lines.mapped('sim_total_cost_tax_excl'))
            total_sale = sum(lines.mapped('sim_total_price_tax_excl'))

            wizard.simulated_margin = total_sale - total_purchase
            wizard.total_amount_sim_tax_incl = sum(lines.mapped('sim_total_price_tax_incl'))
            wizard.total_amount_sim_tax_excl = sum(lines.mapped('sim_total_price_tax_excl'))
            wizard.total_simulated_cost_tax_excl = sum(lines.mapped('sim_total_cost_tax_excl'))
            wizard.simulated_margin_percent = (1 - total_purchase / total_sale) if total_sale else 0.0

    def name_get(self):
        return [
            (
                record.id,
                f"Gestion prix {'devis' if record.order_id.state == 'draft' else 'commande'} {record.order_id.name}",
            )
            for record in self
        ]

    def action_button_simulate(self):
        self.ensure_one()
        self.compute(dry_run=True)

    def action_bouton_validate(self):
        self.ensure_one()
        self.compute(dry_run=False)

    def action_button_cancel(self):
        return {'type': 'ir.actions.client', 'tag': 'history_back'}

    def _do_apply(self, values):
        line_obj = self.env['sale.order.line']
        for line, vals in values.items():
            if isinstance(line, int):  # should be a new line
                line = line_obj.create(vals)
            else:
                line.write(vals)

    def _do_compute(self, total, mode, currency, calculation_basis, line_rounding):
        values = self.line_ids.distribute_amount(total, mode, currency, calculation_basis, line_rounding)
        # on conserve la fonction de calcul des prix simulés, pour se servir des résultats pour les montant de remise
        # puis on réinitialise les montants simulés des lignes pour ne pas induire en erreur les utilisateurs
        # ne pas créer de ligne de remise quand on remet au prix magasin
        if self.discount_mode == 'total' and self.discount_type != 'reset':
            self._do_compute_discount_total(values)
        return values

    def _do_compute_discount_total(self, values):
        old_res = values
        values = {}

        line_by_tax = {}
        # grouper les lignes par taxes. On utilise des tuples pour ne pas qu'une ligne se retrouve dans 2 groupes
        for product_line in self.line_ids.filtered(lambda line: not line.is_discount and line.state == 'included'):
            taxes_ids = tuple(product_line.order_line_id.tax_id.ids)
            if taxes_ids in line_by_tax:
                line_by_tax[taxes_ids] |= product_line
            else:
                line_by_tax[taxes_ids] = product_line

        for idx, (taxes_ids, associated_lines) in enumerate(line_by_tax.items(), start=1):
            price_unit = 0
            product_uom = self.env.ref('uom.product_uom_unit')
            for order_line in associated_lines.mapped('order_line_id'):
                if order_line in old_res:
                    vals = old_res[order_line]
                    price_unit -= (
                        (order_line.price_unit - vals['price_unit'])
                        * (1 - (order_line.discount or 0.0) / 100.0)
                        * order_line.product_uom._compute_quantity(order_line.product_uom_qty, product_uom)
                    )

            if price_unit:
                line_vals = {
                    'wizard_id': self.id,
                    'is_discount': True,
                    'discount_tax_ids': [(6, 0, list(taxes_ids))],
                    'prix_unit_create': price_unit,
                }
                new_line = self.env['of.sale.price.management.wizard.line'].new(line_vals)
                new_line.sim_total_price_tax_excl = sum(associated_lines.mapped('sim_total_price_tax_excl')) - sum(
                    associated_lines.mapped('order_line_id.price_subtotal')
                )
                new_line.sim_total_price_tax_incl = sum(associated_lines.mapped('sim_total_price_tax_incl')) - sum(
                    associated_lines.mapped('order_line_id.price_total')
                )

                values[idx] = new_line.get_values_order_line_create()
                self.line_ids |= new_line

        for product_line in self.line_ids.filtered(lambda line: not line.is_discount and line.state == 'included'):
            product_line.sim_total_price_tax_excl = product_line.total_price_tax_excl
            product_line.sim_total_price_tax_incl = product_line.total_price_tax_incl
            product_line.sim_total_cost_tax_excl = product_line.total_cost_tax_excl

        for forced_line in self.line_ids.filtered(lambda line: not line.is_discount and line.state == 'forced'):
            if forced_line.order_line_id in old_res:
                values[forced_line.order_line_id] = old_res[forced_line.order_line_id]

    def _check_data(self):
        if self.discount_type == 'total_target_amnt_tax_incl':
            if self.value <= 0:
                raise UserError(_("You must enter a target total amount incl. VAT."))
        elif self.discount_type == 'total_target_amnt_tax_excl':
            if self.value <= 0:
                raise UserError(_("You must enter a target total amount excl. VAT."))
        elif self.discount_type == 'amount_tax_incl':
            if not self.value:
                raise UserError(_("You must enter an amount incl. VAT to deduct."))
            if self.value > self.init_total_amount_tax_incl:
                raise UserError(
                    _(
                        "The amount including VAT to be deducted is greater than the total amount including VAT of "
                        "items to which the discount applies."
                    )
                )
        elif self.discount_type == 'amount_tax_excl':
            if not self.value:
                raise UserError(_("You must enter an amount to be deducted."))
            if self.value > self.init_total_amount_tax_excl:
                raise UserError(
                    _(
                        "The amount excluding VAT to be deducted is greater than the total amount excluding VAT of "
                        "items on which the discount is applied."
                    )
                )
        elif self.discount_type == 'percentage':
            if not 0 < self.value <= 100:
                raise UserError(_("The discount percentage must be greater than 0 and less than or equal to 100."))
        elif self.discount_type == 'margin_percent':
            if self.value >= 100:
                raise UserError(_("The margin percentage must be less than 100."))
        elif self.discount_type != 'restore':
            return False

    def compute(self, dry_run=False):
        """
        Calcule les nouveaux prix des articles sélectionnés en fonction de la méthode de calcul choisie.
        """
        self.ensure_one()

        # Check data entered by the user
        self._check_data()

        # Remove old discount lines if any
        self.line_ids.filtered(lambda line: line.is_discount).unlink()

        # Paramètre d'arrondi
        if self.rounding_mode == 'no_rounding':
            line_rounding = False
        elif self.rounding_precision:
            line_rounding = {'field': self.rounding_mode, 'precision': int(self.rounding_precision)}
        else:
            raise UserError(_("You must select the rounding precision"))

        # On détermine le montant TTC cible en fonction de la méthode de calcul choisie
        order = self.order_id
        if self.discount_type == 'total_target_amnt_tax_incl':
            mode = 'taxes_incl'
            total = self.value
        elif self.discount_type == 'total_target_amnt_tax_excl':
            mode = 'taxes_excl'
            total = self.value
        elif self.discount_type == 'amount_tax_incl':
            mode = 'taxes_incl'
            total = order.amount_total - self.value
        elif self.discount_type == 'amount_tax_excl':
            mode = 'taxes_excl'
            total = order.amount_untaxed - self.value
        elif self.discount_type == 'percentage':
            mode = 'taxes_incl'
            total = order.amount_total * (1 - self.value / 100.0)
        elif self.discount_type == 'margin_percent':
            mode = 'taxes_excl'
            total = (100 * order.of_total_cost) / (100.0 - self.value)
            self = self.with_context(margin_percent=True)
        else:
            mode = 'restore'
            total = False

        cur = order.pricelist_id.currency_id
        calculation_basis = (
            self.discount_type
            in ['total_target_amnt_tax_incl', 'total_target_amnt_tax_excl', 'amount_tax_incl', 'amount_tax_excl']
            and self.calculation_basis
            or 'price'
        )
        values = self._do_compute(total, mode, cur, calculation_basis, line_rounding)

        # Dry run, we don't want to write anything
        if dry_run:
            return

        total_tax_incl_init = order.amount_total
        self._do_apply(values)
        total_tax_incl_end = order.amount_total

        # On ajoute le libellé de la remise dans les notes du devis si case cochée
        if self.display_discount:
            text = _("Exceptional discount deducted of %s.\n") % format_amount(
                self.env, total_tax_incl_init - total_tax_incl_end, cur
            )
            order.note = text + (order.note or '')
        # Updates the payment schedule
        order.message_post(body=_("Price management applied."))

    def action_button_include_all(self):
        self.line_ids.filtered(lambda line: line.state != 'included' and not line.product_forbidden_discount).write(
            {'state': 'included'}
        )

    def action_button_exclude_all(self):
        self.line_ids.filtered(lambda line: line.state == 'included').write({'state': 'excluded'})

    def action_button_toggle_view_mode(self):
        """Allows you to switch between the vendor/customer view"""
        for record in self:
            record.customer_view = not record.customer_view
            record.order_id.of_customer_view = record.customer_view

    def action_price_management_print(self):
        self.ensure_one()
        return self.env.ref('of_sale_price_management.of_action_report_sale_price_management').report_action(self)

    @api.model
    def report_get_report_name(self, docs):
        return _("Margin sheet")

    @api.model
    def report_get_report_number(self, docs):
        return ' / '.join(docs.mapped('order_id').mapped('name'))

    @api.model
    def report_get_report_date(self, records):
        return ' / '.join([fields.Date.to_string(rec.order_id.date_order) for rec in records])

    def report_get_lines(self):
        """Returns data for the lines table in the report."""
        self.ensure_one()
        return self.line_ids.filtered(lambda line: line.state == 'included')

    def report_get_summary_lines(self):
        """Returns data for the summary table at the bottom of the report."""
        self.ensure_one()
        order_lines = self.line_ids.filtered(lambda line: line.state == 'included').mapped('order_line_id')
        order_lines_product = order_lines.filtered(lambda oline: oline.product_id.type != 'service')
        order_lines_service = order_lines.filtered(lambda oline: oline.product_id.type == 'service')
        currency_symbol = self.currency_id.symbol
        res = []
        for name, lines in [
            (_("Products"), order_lines_product),
            (_("Services"), order_lines_service),
            (_("Total"), order_lines),
        ]:
            lines_dict = {'name': name}
            total_purchase = 0.0
            for line in lines:
                total_purchase += line.purchase_price * line.product_uom_qty
            total_sale = sum(lines.mapped('price_subtotal'))
            lines_dict['cost'] = f'{total_purchase:.2f} {currency_symbol}'
            lines_dict['sale'] = f'{total_sale:.2f} {currency_symbol}'
            lines_dict['margin'] = f'{total_sale:.2f} {currency_symbol}'
            margin_percent = (100 * (1 - total_purchase / total_sale)) if total_sale else 0.0
            lines_dict['margin_percent'] = f'{margin_percent:.2f}' if total_sale else '- %'
            res.append(lines_dict)
        return res


class OFPriceManagementWizardLine(models.TransientModel):
    _name = 'of.sale.price.management.wizard.line'
    _description = "Selection of products from a quote/order form"

    # TODO: Déselectionner les lignes dont la quantité ou le prix valent 0
    state = fields.Selection(
        selection=[('excluded', "Excluded"), ('included', "Included"), ('forced', "Forced")],
        string="State",
        required=True,
        default='included',
    )
    wizard_id = fields.Many2one(comodel_name='of.sale.price.management.wizard', required=True, ondelete='cascade')
    order_line_id = fields.Many2one(comodel_name='sale.order.line', string="Product", readonly=True, ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string="Product", compute='_compute_product_id')
    name = fields.Char(string="Name", compute='_compute_product_id')
    currency_id = fields.Many2one(compute='_compute_currency_id', comodel_name='res.currency', string="Currency")
    quantity = fields.Float(string="Quantity", compute='_compute_quantity')
    tax_ids = fields.Many2many(
        comodel_name='account.tax',
        string="Taxes",
        relation='of_sale_order_gestion_prix_line_discount_tax_rel',
        column1='line_id',
        column2='tax_id',
        compute='_compute_tax_ids',
    )

    total_cost_tax_excl = fields.Monetary(string="Total initial cost excl. VAT", compute='_compute_prices')
    price_unit_tax_excl = fields.Monetary(string="Initial unit price excl. VAT", compute='_compute_prices')
    price_unit_tax_incl = fields.Monetary(string="Initial unit price excl. VAT", compute='_compute_prices')
    total_price_tax_excl = fields.Monetary(string="Initial total price excl. VAT", compute='_compute_prices')
    total_price_tax_incl = fields.Monetary(string="Initial total price incl. VAT", compute='_compute_prices')
    discount = fields.Float(related='order_line_id.discount', readonly=True)

    sim_total_price_tax_incl = fields.Monetary(string="Simulated total price incl. VAT", readonly=True)
    sim_total_price_tax_excl = fields.Monetary(string="Simulated total price excl. VAT")
    sim_total_cost_tax_excl = fields.Monetary(string="Simulated total cost excl. VAT", readonly=True)
    margin = fields.Monetary(string="Margin excl. VAT", compute='_compute_margins')
    margin_percent = fields.Float(string="% Margin", compute='_compute_margins')
    customer_view = fields.Boolean(string="Customer/Vendor view", related="wizard_id.customer_view")
    discount_tax_ids = fields.Many2many(
        comodel_name='account.tax',
        string="Taxes",
        relation='of_sale_order_price_management_line_discount_tax_rel',
        column1='line_id',
        column2='tax_id',
    )
    is_discount = fields.Boolean(string="Is a discount line")
    prix_unit_create = fields.Monetary(
        string="Unit price",
        help="Technical field to store the unit price of the product when creating a new order line",
    )

    def _compute_currency_id(self):
        for line in self:
            line.currency_id = line.order_line_id.currency_id or line.wizard_id.currency_id

    @api.depends('order_line_id', 'is_discount', 'discount_tax_ids')
    def _compute_product_id(self):
        for line in self:
            order_line = line.order_line_id
            line.total_cost_tax_excl = order_line.purchase_price * order_line.product_uom_qty
            if not line.is_discount:
                line.product_id = line.order_line_id.product_id.id
                line.name = line.order_line_id.name
            else:
                line.product_id = line.wizard_id.discount_product_id.id
                line.name = (
                    f"{line.wizard_id.discount_product_id.name} "
                    f"({' + '.join(line.discount_tax_ids.mapped('name'))})"
                )

    @api.depends('order_line_id', 'is_discount')
    def _compute_quantity(self):
        for line in self:
            line.quantity = 1 if line.is_discount else line.order_line_id.product_uom_qty

    @api.depends('order_line_id', 'discount_tax_ids')
    def _compute_tax_ids(self):
        for line in self:
            if line.order_line_id:
                line.tax_ids = line.order_line_id.tax_id.ids
            else:
                line.tax_ids = line.discount_tax_ids.ids

    @api.depends('order_line_id', 'is_discount')
    def _compute_prices(self):
        for product_line in self.filtered(lambda line: line.is_discount):
            product_line.total_cost_tax_excl = 0
            product_line.price_unit_tax_excl = 0
            product_line.price_unit_tax_incl = 0
            product_line.total_price_tax_excl = 0
            product_line.total_price_tax_incl = 0
        for product_line in self.filtered(lambda line: not line.is_discount):
            order_line = product_line.order_line_id
            product_line.total_cost_tax_excl = order_line.purchase_price * order_line.product_uom_qty
            product_line.price_unit_tax_excl = order_line.price_reduce_taxexcl
            product_line.price_unit_tax_incl = order_line.price_reduce_taxinc
            product_line.total_price_tax_excl = order_line.price_subtotal
            product_line.total_price_tax_incl = order_line.price_total

    @api.depends('sim_total_price_tax_excl', 'sim_total_cost_tax_excl')
    def _compute_margins(self):
        for line in self:
            purchase_amount = line.sim_total_cost_tax_excl
            sale_amount = line.sim_total_price_tax_excl
            line.margin = sale_amount - purchase_amount
            line.margin_percent = 100.0 * (1 - purchase_amount / sale_amount) if sale_amount else 0.0

    @api.depends('sim_total_price_tax_excl', 'total_price_tax_excl')
    def _compute_sim_total_price_tax_incl(self):
        for line in self:
            sim_total_price_tax_incl = 0.0
            if line.total_price_tax_excl:
                factor = line.sim_total_price_tax_excl / line.total_price_tax_excl
                sim_total_price_tax_incl = line.total_price_tax_incl * factor
            line.sim_total_price_tax_incl = sim_total_price_tax_incl

    @api.onchange('margin_percent')
    def _onchange_margin_percent(self):
        for line in self:
            # Margin percent cannot be greater than 100% if the initial price is not null
            margin_percent_max = 100.0 if line.total_cost_tax_excl == 0 else 99.99
            line.margin_percent = min(line.margin_percent, margin_percent_max)
            margin_percent = (
                100.0 * (1 - line.sim_total_cost_tax_excl / line.sim_total_price_tax_excl)
                if line.sim_total_price_tax_excl
                else -100.0
            )
            if float_compare(margin_percent, line.margin_percent, precision_rounding=0.01):
                line.sim_total_price_tax_excl = line.sim_total_cost_tax_excl and line.sim_total_cost_tax_excl * (
                    100 / (100 - line.margin_percent)
                )

    def get_values_order_line_create(self):
        self.ensure_one()
        if not self.is_discount:
            return {}
        return {
            'order_id': self.wizard_id.order_id.id,
            'name': self.name,
            'product_id': self.product_id.id,
            'product_uom': self.env.ref('uom.product_uom_unit').id,
            'price_unit': self.prix_unit_create,
            'tax_id': [(6, 0, [self.discount_tax_ids.ids])],
            'customer_lead': 0,
        }

    def _get_distributed_amount(
        self, to_distribute, total, currency, calculation_basis, rounding, line_rounding, all_zero
    ):
        """This function calculates the new amount to allocate to the order line passed in parameter.
        It returns a dictionary of values to modify on this line.

        :param to_distribute: Amount remaining to be distributed
        :type to_distribute: _type_
        :param total: Current cumulative amount of order lines not yet recalculated
        :type total: _type_
        :param currency: Currency used
        :type currency: _type_
        :param calculation_basis: The calculation basis for the prorata. Can be 'price', 'cost'
            (or 'total_cost' if 'of_sale_budget' module is installed)
        :type calculation_basis: _type_
        :param rounding: Boolean determining whether the unit price should be rounded
        :type rounding: _type_
        :param line_rounding: Line rounding rule on the total amount of the line
        :type line_rounding: dict
        :   {'field': self.rounding_mode, 'precision': int(self.rounding_precision)} or False
        :param all_zero: _description_
        :type all_zero: _type_
        :return: Tuple of values to modify on the order line
        :rtype: tuple
        """
        self.ensure_one()
        order_line = self.order_line_id
        if to_distribute == 0.0:
            line_vals = {'price_unit': 0.0}
            taxes = order_line.tax_id.with_context(base_values=(0.0, 0.0, 0.0))
            taxes = taxes.compute_all(
                0.0,
                currency,
                order_line.product_uom_qty,
                product=order_line.product_id,
                partner=order_line.order_id.partner_id,
            )
        else:
            # Prix HT unitaire final de la ligne
            taxes = order_line.tax_id
            if total == 0.0:  # Permet de gérer les lignes de remises avec montant HT initial de 0
                if self._context.get('margin_percent'):  # Dans le cas d'un calcul de % de marge on part du montant HT
                    taxes_percentage = 0.0
                else:  # Dans tous les autres cas, on part du montant TTC
                    taxes_percentage = sum(taxes.mapped('amount')) / 100
                price_unit = (
                    self._get_base_amount(order_line, calculation_basis, all_zero)
                    * to_distribute
                    / (1 + taxes_percentage)
                )
            else:
                price_unit = self._get_base_amount(order_line, calculation_basis, all_zero) * to_distribute / total
            if rounding:
                price_unit = currency.round(price_unit)

            # Ces deux lignes sont copiées depuis la fonction sale_order_line._compute_amount() d module sale
            price = price_unit * (1 - (order_line.discount or 0.0) / 100.0) * order_line.product_uom_qty
            taxes = taxes.with_context(base_values=(price, price, price)).compute_all(
                price,
                currency,
                order_line.product_uom_qty,
                product=order_line.product_id,
                partner=order_line.order_id.partner_id,
            )

            if line_rounding:
                # On arrondit les montants par ligne
                montant = taxes['total_excluded']
                if line_rounding['field'] == 'total_included':
                    montant += sum(tax['amount'] for tax in taxes['taxes'])

                montant_arrondi = round(montant, line_rounding['precision'])
                if float_compare(montant_arrondi, montant, precision_rounding=0.01):
                    ratio = montant_arrondi / montant
                    price_unit *= ratio
                    # Recalcul des taxes pour l'affichage de la simulation
                    price = price_unit * (1 - (order_line.discount or 0.0) / 100.0) * order_line.product_uom_qty
                    taxes = order_line.tax_id.with_context(base_values=(price, price, price))
                    taxes = taxes.compute_all(
                        price,
                        currency,
                        order_line.product_uom_qty,
                        product=order_line.product_id,
                        partner=order_line.order_id.partner_id,
                    )

            price_management_variation = price_unit - order_line.price_unit + order_line.of_price_management_variation
            new_price_variation = price_management_variation - (price_unit * (order_line.discount or 0.0) / 100.0)

            line_vals = {
                'price_unit': price_unit,
                'of_price_management_variation': price_management_variation,
                'of_unit_price_variation': new_price_variation,
            }
        return {order_line: line_vals}, taxes

    def _get_restore_amount(self, line_rounding):
        self.ensure_one()
        order_line = self.order_line_id

        # Appel à of_get_price_unit() pour recalculer le prix unitaire
        price_unit = order_line.of_get_price_unit()
        if line_rounding:
            price = price_unit * (1 - (order_line.discount or 0.0) / 100.0) * order_line.product_uom_qty
            taxes = order_line.tax_id.with_context(base_values=(price, price, price), round=False)
            taxes = taxes.compute_all(
                price,
                order_line.currency_id,
                order_line.product_uom_qty,
                product=order_line.product_id,
                partner=order_line.order_id.partner_id,
            )

            # On arrondit les montants par ligne
            amount = taxes[line_rounding['field']]
            rounded_amount = round(amount, line_rounding['precision'])
            ratio = rounded_amount / amount
            price_unit *= ratio

        # Calcul des taxes pour l'affichage de la simulation
        price = price_unit * (1 - (order_line.discount or 0.0) / 100.0) * order_line.product_uom_qty
        taxes = order_line.tax_id.with_context(base_values=(price, price, price))
        taxes = taxes.compute_all(
            price,
            order_line.currency_id,
            order_line.product_uom_qty,
            product=order_line.product_id,
            partner=order_line.order_id.partner_id,
        )

        new_price_variation = -price_unit * (order_line.discount or 0.0) / 100.0
        return (
            {
                order_line: {
                    'price_unit': price_unit,
                    'of_price_management_variation': 0.0,
                    'of_unit_price_variation': new_price_variation,
                    'purchase_price': order_line.product_id.get_cost(),
                }
            },
            taxes,
        )

    def _get_sorted_lines(self):
        """Return the lines of the wizard sorted by quantity.
        The new prices are applied to the lines in descending order of quantity sold.
        This allows you to adjust the price on the last lines more easily

        :return of.sale.price.management.wizard.line: The lines of the wizard sorted by quantity
        """
        return self.sorted('quantity', reverse=True)

    def _update_values_and_lines_total(self, values, vals, taxes, line):
        values.update(vals)

        # Update wizard lines
        line.sim_total_price_tax_excl = taxes['total_excluded']
        line.sim_total_price_tax_incl = taxes['total_included']

    def distribute_amount(self, to_distribute, mode, currency, calculation_basis, line_rounding):
        """Function to distribute an amount on the different lines of the wizard.
        This function directly modifies the lines of the wizard and returns the values to be modified on the order.

        :param to_distribute: Amount to distribute
        :param mode: Computation mode (ht, ttc or restore)
        :param currency: Currency used
        :param calculation_basis: The calculation basis for the prorata. Can be 'price', 'cost'
        :param line_rounding: Rule for rounding the total amount of the line
        :type line_rounding: dict or False
            {'field': wizard.rounding_mode, 'precision': int(wizard.rounding_precision)} or False
        :return: Values to update on the order lines
        :rtype: dict
        """
        round_tax = self.env.user.company_id.tax_calculation_rounding_method != 'round_globally'

        lines_select = self.filtered(lambda line: line.state == 'included')
        if mode != 'restore':
            lines_select = lines_select.filtered(lambda line: line.order_line_id.price_unit) or lines_select
        lines_forced = self.filtered(lambda line: line.state == 'forced')
        lines_excluded = self - lines_select - lines_forced

        # Les totaux des lignes non sélectionnées sont gardés en précision standard
        if mode == 'taxes_excl':
            amount_tax_excl = sum(lines_excluded.mapped('order_line_id').mapped('price_subtotal'))
            tax_field = 'total_excluded'
        else:
            amount_tax_excl = sum(lines_excluded.mapped('total_price_tax_incl'))
            tax_field = 'total_included'

        values = {}

        # Les totaux des lignes forcées sont gardés en précision standard
        order_lines = lines_select.with_context(round=False).mapped('order_line_id')
        all_zero = False
        # Vérification si toutes les lignes sont a 0 en fonction du prorata choisi
        if calculation_basis == 'cost':
            all_zero = all(purchase_price == 0.0 for purchase_price in order_lines.mapped('purchase_price'))
        elif calculation_basis == 'price':
            all_zero = all(price_unit == 0.0 for price_unit in order_lines.mapped('price_unit'))
        total_forced = 0
        for lf in lines_forced:
            vals, taxes = lf._get_distributed_amount(
                lf.sim_total_price_tax_excl,
                lf.total_cost_tax_excl if calculation_basis != 'price' else lf.total_price_tax_excl,
                currency=currency,
                calculation_basis=calculation_basis,
                rounding=True,
                line_rounding=False,
                all_zero=True,
            )

            if not round_tax:
                amount_tax = sum(tax['amount'] for tax in taxes['taxes'])
                taxes.update({'total_excluded': taxes['base'], 'total_included': taxes['base'] + amount_tax})

            self._update_values_and_lines_total(values, vals, taxes, lf)
            total_forced += taxes[tax_field]

        total_unselected = amount_tax_excl + total_forced

        # Les totaux des lignes sélectionnées sont calculés en précision maximale
        total_selected = 0.0
        line_taxes = {}
        for line in lines_select.with_context(round=False):
            # Calcul manuel des taxes avec context['round']==False pour conserver la précision des calculs
            order_line = line.order_line_id
            price = self._get_base_amount(order_line, calculation_basis, all_zero) * (
                1 - (order_line.discount or 0.0) / 100.0
            )
            taxes = order_line.tax_id.compute_all(
                price,
                order_line.currency_id,
                order_line.product_uom_qty,
                product=order_line.product_id,
                partner=order_line.order_id.partner_id,
            )
            total_selected += taxes[tax_field]
            line_taxes[line.id] = taxes

        lines_select = lines_select._get_sorted_lines()

        to_distribute -= total_unselected
        for line in lines_select:
            if mode == "restore":
                vals, taxes = line._get_restore_amount(line_rounding=line_rounding)
                line.sim_total_cost_tax_excl = (
                    line.order_line_id.product_id.get_cost() * line.order_line_id.product_uom_qty
                )
            else:
                vals, taxes = line._get_distributed_amount(
                    to_distribute,
                    total_selected,
                    currency=currency,
                    calculation_basis=calculation_basis,
                    # On arrondit toutes les lignes sauf la dernière
                    rounding=line != lines_select[-1],
                    line_rounding=line_rounding,
                    all_zero=all_zero,
                )
            # Recalcul de 'total_excluded' et 'total_included' sans les arrondis
            if not round_tax:
                amount_tax = sum(tax["amount"] for tax in taxes['taxes'])
                taxes.update(
                    {
                        "total_excluded": taxes['base'],
                        "total_included": taxes['base'] + amount_tax,
                    }
                )

            if mode != "restore":
                to_distribute -= taxes[tax_field]
                total_selected -= line_taxes[line.id][tax_field]

            self._update_values_and_lines_total(values, vals, taxes, line)
        for line in lines_excluded:
            line.sim_total_price_tax_excl = line.order_line_id.price_subtotal
            line.sim_total_price_tax_incl = line.order_line_id.price_total
        return values

    @api.model
    def _get_base_amount(self, order_line, calculation_basis, all_zero):
        """Return the base amount for the prorata calculation

        :param order_line: order line on which we retrieve the information
        :param calculation_basis: Type of prorata used
        :param all_zero: True if calculation_basis == 'cost' and all purchase prices are 0,
            if calculation_basis == 'price' and all price units are 0, False in other cases
        :return: the base amount
        :rtype: float
        """
        if calculation_basis == 'cost':
            return order_line.purchase_price or all_zero and 1.0 or 0.0
        else:
            return order_line.price_unit or all_zero and 1.0 or 0.0
