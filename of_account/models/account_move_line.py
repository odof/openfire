# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.models import regex_order

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = ["account.move.line", "of.readgroup"]

    @api.model
    def default_get(self, fields_list):
        result = super().default_get(fields_list)

        lines = self._context.get("line_ids")
        journal_id = self._context.get("journal_id")
        if not journal_id or not lines:
            return result

        lines = self.env["account.move"].new({"line_ids": self._context["line_ids"]})["line_ids"]
        journal = self.env["account.journal"].browse(journal_id)

        if journal.type in ("bank", "cash"):
            if len(lines) == 1:
                account = lines.account_id
                if account and account.account_type in ("liability_payable", "asset_receivable"):
                    result.update(
                        {
                            "account_id": journal.default_account_id.id,
                            "debit": lines.credit,
                            "credit": lines.debit,
                            "date_maturity": lines.date_maturity,
                        }
                    )
        elif journal.type == "purchase":
            len_lines = len(lines)
            if len_lines in {1, 2}:
                if account := lines[-1].account_id:
                    tax_type = "purchase"
                    for tax in account.of_account_counterpart_id.tax_ids if len_lines == 1 else account.tax_ids:
                        if tax.type_tax_use == tax_type:
                            break
                    else:
                        tax = False
                    if tax or len_lines == 1:
                        account = account.of_account_counterpart_id if len_lines == 1 else tax.account_id
                        tax_amount = tax and tax.amount or 0
                        result.update(
                            {
                                "account_id": account and account.id or False,
                                "debit": lines[0].credit / (100 + tax_amount) * (100 if len_lines == 1 else tax_amount),
                                "credit": lines[0].debit / (100 + tax_amount) * (100 if len_lines == 1 else tax_amount),
                                "date_maturity": lines.date_maturity,
                            }
                        )
        return result

    price_unit = fields.Float(  # Override to add help text
        help="Unit price of the product. To enter without VAT or with VAT according to the invoice line.",
    )
    of_product_categ_id = fields.Many2one(
        comodel_name="product.category",
        related="product_id.categ_id",
        string="Product category",
        readonly=True,
        store=True,
        index=True,
    )
    of_date_invoice = fields.Date(related="move_id.invoice_date", string="Invoice/Bill Date", store=True, index=True)
    of_name = fields.Char(string="Name", compute="_compute_of_name", readonly=False, store=True)
    of_gb_partner_tag_id = fields.Many2one(
        comodel_name="res.partner.category",
        compute=lambda *a, **k: {},
        search="_search_of_gb_partner_tag_id",
        string="Partner tag",
        of_custom_groupby=True,
    )
    of_price_unit_taxexcl = fields.Float(
        string="Unit Price Tax excl",
        compute="_compute_of_price_unit",
        digits="Product Price",
        store=True,
        precompute=True,
        help="Unit price without taxes",
    )
    of_price_unit_taxinc = fields.Float(
        string="Unit Price Tax incl",
        compute="_compute_of_price_unit",
        digits="Product Price",
        store=True,
        precompute=True,
        help="Unit price with taxes",
    )
    of_unit_price_taxexcl_display = fields.Boolean(
        string="Display unit price tax excl",
        compute="_compute_of_unit_price_taxexcl_display",
    )

    # ----------------------------------------------------------
    # Compute methods
    # ----------------------------------------------------------

    @api.depends("product_id")
    def _compute_name(self):
        if self._context.get("of_only_default_code"):
            self = self.with_context(of_only_default_code=False)
        super(AccountMoveLine, self)._compute_name()

    @api.depends("name", "move_id.state")
    def _compute_of_name(self):
        for line in self:
            move = line.move_id
            if move.state == "posted":
                updated_ref = (
                    f"{(move.partner_id.name or move.partner_id.parent_id.name or ''):.30} {move.name.strip()}"  # noqa
                )
                if move.is_purchase_document():
                    # Add the supplier reference to the invoice reference when we are in a supplier invoice
                    updated_ref = f"{updated_ref} {move.ref or ''}".rstrip()
                line.of_name = updated_ref
            else:
                line.of_name = line.name

    @api.depends("display_type", "company_id", "partner_id")
    def _compute_account_id(self):
        def _first_line_create(lines):
            """Return True if the first line is being created"""
            return lines[0][0] == 0 and len(lines) == 1 if lines else True

        for line in self.filtered(lambda line: line.display_type not in ("line_section", "line_note")):
            if line.partner_id and not line.account_id and _first_line_create(self._context.get("line_ids", [])):
                supplier = line.partner_id.supplier_rank > 0
                customer = line.partner_id.customer_rank > 0
                if line.journal_id.type == "purchase" or (line.journal_id.type != "sale" and supplier and not customer):
                    # For a purchase journal, take the partner's account payable.
                    # For a journal that is not a sale one, take the partner's account payable if the partner
                    # is a supplier and not a customer.
                    line.account_id = line.partner_id.property_account_payable_id
                else:
                    # For any other journal, take the partner's account receivable.
                    line.account_id = line.partner_id.property_account_receivable_id
        super()._compute_account_id()

    @api.depends("price_unit", "product_id", "tax_ids", "currency_id", "move_id.partner_id")
    def _compute_of_price_unit(self):
        for line in self:
            prices = line.tax_ids.compute_all(
                line.price_unit,
                currency=line.currency_id,
                quantity=1,
                product=line.product_id,
                partner=line.move_id.partner_id,
            )
            line.of_price_unit_taxexcl = prices["total_excluded"]
            line.of_price_unit_taxinc = prices["total_included"]

    def _compute_of_unit_price_taxexcl_display(self):
        for line in self:
            line.of_unit_price_taxexcl_display = line.price_unit != line.of_price_unit_taxexcl

    # ---------------------------------------------------------
    # ORM methods
    # ---------------------------------------------------------

    def _valid_field_parameter(self, field, name):
        # EXTENDS models
        return name == "of_custom_groupby" or super()._valid_field_parameter(field, name)

    def _search_of_gb_partner_tag_id(self, operator, value):
        return [("partner_id.category_id", operator, value)]

    @api.model
    def _read_group_process_groupby(self, gb, query):
        """Override to add the possibility to group by customer tag"""
        if gb != "of_gb_partner_tag_id":
            return super()._read_group_process_groupby(gb, query)

        split = gb.split(":")
        field = self._fields.get(split[0])
        if not field:
            raise ValueError("Invalid field %r on model %r" % (split[0], self._name))
        field_type = field.type
        alias = query.left_join(
            self._table, "partner_id", "res_partner_res_partner_category_rel", "partner_id", "partner_category"
        )

        return {
            "field": gb,
            "groupby": gb,
            "type": field_type,
            "display_format": None,
            "interval": None,
            "granularity": None,
            "tz_convert": False,
            "qualified_field": f'"{alias}".category_id',
        }

    @api.model
    def of_custom_groupby_generate_order(self, alias, order_field, query, reverse_direction, seen):
        if order_field == "of_gb_partner_tag_id":
            dest_model = self.env["res.partner.category"]
            m2o_order = dest_model._order
            if not regex_order.match(m2o_order):
                # _order is complex, can't use it here, so we default to _rec_name
                m2o_order = dest_model._rec_name
            rel_alias = query.left_join(
                alias, "partner_id", "res_partner_res_partner_category_rel", "partner_id", "partner_category_rel"
            )
            dest_alias = query.left_join(rel_alias, "category_id", "res_partner_category", "id", "partner_category")
            return dest_model._generate_order_by_inner(dest_alias, m2o_order, query, reverse_direction, seen)
        return []

    # ---------------------------------------------------------
    # Actions methods
    # ---------------------------------------------------------

    def action_button_open_account_move_line(self):
        """Open the account move line in a new window."""
        self.ensure_one()
        form_id = self.env.ref("of_account.of_account_move_line_form").id
        return {
            "name": _("Account Move Line"),
            "view_mode": "form",
            "res_model": "account.move.line",
            "res_id": self.id,
            "views": [(form_id, "form")],
            "type": "ir.actions.act_window",
            "target": "new",
        }

    def reconcile(self):
        """Override of account.move.line.reconcile to set the name of the move with the partner name and the
        invoice number."""
        res = super().reconcile()
        move_lines = self.filtered(
            lambda line: (line.reconciled or len(line.matched_debit_ids) == 1)
            and line.payment_id
            and line.account_id.reconcile
        )
        for line in move_lines:
            debit_lines = line.matched_debit_ids.mapped("debit_move_id")
            moves = debit_lines.mapped("move_id")
            if len(moves) == 1:
                name_infos = [
                    f"{(moves.partner_id.name or moves.partner_id.parent_id.name or ''):.30}",  # noqa
                    moves.name,
                ]  # noqa
                name = " ".join([value for value in name_infos if value])
                # TODO, FIXME: Should we write this new reference on the move ? This move already has a reference,
                # that is the payment reference. This reference is used in the bank statement reconciliation.
                line.move_id.line_ids.with_context(check_move_validity=False).write({"of_name": name})
                try:
                    line.move_id.write({"ref": name})
                except UserError:
                    # With some module as OCA account_lock_date, the write can raise an error
                    # It must not be blocking for the reconciliation
                    _logger.debug(
                        f"An error occurred while writing on account.move {line.move_id.id} after reconcilation"
                    )
        return res
