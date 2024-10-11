# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    of_exported = fields.Boolean(string="Exported", readonly=True, copy=False)
    of_customer_category_ids = fields.Many2many(
        comodel_name="res.partner.category", related="partner_id.category_id", string="Customer tags"
    )
    of_partner_phone = fields.Char(related="partner_id.phone", string="Partner's phone", readonly=True)
    of_partner_mobile = fields.Char(related="partner_id.mobile", string="Partner's mobile", readonly=True)
    of_partner_email = fields.Char(related="partner_id.email", string="Partner email", readonly=True)
    ref = fields.Char(compute="_compute_ref", readonly=False, store=True)

    @api.constrains("company_id", "journal_id")
    def _check_journal_company(self):
        company_obj = self.env["res.company"]
        for move in self.filtered(lambda m: m.journal_id and not m.name):
            if move.journal_id.company_id not in company_obj.search([("id", "parent_of", move.company_id.id)]):
                raise ValidationError(_("The journal's company must be the same as the move entry's company."))

    # -------------------------------------------------------------------------
    # Onchange methods
    # -------------------------------------------------------------------------

    @api.onchange("partner_id")
    def _onchange_partner_id_warning(self):
        partner = self.partner_id
        # If partner has no warning, check its parents
        # invoice_warn is shared between different objects
        if not partner.of_is_account_warn and partner.parent_id:
            partner = partner.parent_id

        if partner.of_is_account_warn and partner.invoice_warn != "no-message":
            return super()._onchange_partner_id_warning()
        return

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    def _get_suitable_default_type_domain(self):
        """For inheritance purpose"""
        suitable_default_type_domain = (
            self.env["ir.config_parameter"].sudo().get_param("of.account.suitable_default_type_domain")
        )
        types_domain = suitable_default_type_domain.split(",") if suitable_default_type_domain else ["general"]
        return list(map(str.strip, types_domain))

    @api.depends()
    def _compute_suitable_journal_ids(self):
        """Override to allow to filter on many journal types when this is not a sale or purchase move."""
        for move in self:
            journal_type = (
                [move.invoice_filter_type_domain]
                if move.invoice_filter_type_domain
                else self._get_suitable_default_type_domain()
            )
            company_id = move.company_id.id or self.env.company.id
            domain = [("company_id", "=", company_id), ("type", "in", journal_type)]
            move.suitable_journal_ids = self.env["account.journal"].search(domain)

    @api.depends("partner_id", "line_ids.partner_id")
    def _compute_commercial_partner_id(self):
        """Override to allow to compute the commercial partner on a move with no partner from its lines.
        Thats avoid to have to set the partner on each line when creating a move from scratch.
        """
        super()._compute_commercial_partner_id()
        for move in self.filtered(lambda m: not m.commercial_partner_id):
            partner = move.line_ids.mapped("partner_id")
            move.commercial_partner_id = partner.commercial_partner_id if len(partner) == 1 else False

    @api.depends("partner_id")
    def _compute_ref(self):
        for move in self:
            if partner := move.partner_id:
                partner_ref = partner.ref
                if not partner_ref and partner.parent_id:
                    partner_ref = partner.parent_id.ref
                move.ref = partner_ref

    # -------------------------------------------------------------------------
    # Public actions
    # -------------------------------------------------------------------------

    def action_post(self):
        if self.filtered(
            lambda move: move.state != "open"
            and move.move_type in ("out_invoice", "out_refund")
            and move.amount_total < 0
        ):
            raise UserError(_("You cannot validate an invoice or a refund with a negative total."))
        return super().action_post()
