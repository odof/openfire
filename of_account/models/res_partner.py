# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    # invoice_warn and invoice_warn_msg are now shared between invoices, sales and interventions
    of_is_account_warn = fields.Boolean(string="Invoices warning")
    of_is_warn = fields.Boolean(string="Warning on at least one object", compute="_compute_of_is_warn", store=True)
    invoice_warn = fields.Selection(help="Warning type", compute="_compute_invoice_warn", store=True)
    of_warn_block = fields.Boolean(string="Blocking")

    @api.onchange("parent_id", "property_account_receivable_id")
    def _onchange_property_account_receivable_id(self):
        if (
            self._origin.property_account_receivable_id
            and self.property_account_receivable_id
            and self.env["account.move.line"].search(
                [
                    (
                        "account_id",
                        "=",
                        self._origin.property_account_receivable_id.id,
                    )
                ]
            )
        ):
            return {
                "warning": {
                    "title": _("Warning"),
                    "message": _(
                        "If you save, you'll be editing an accounting account that contains entries. "
                        "If you are sure you can continue, otherwise please do not save and cancel this "
                        "modification (from: %s, to: %s)."
                    )
                    % (
                        self._origin.property_account_receivable_id.name,
                        self.property_account_receivable_id.name,
                    ),
                }
            }

    @api.depends("of_is_account_warn")
    def _compute_of_is_warn(self):
        """This function should be inherited in childs module"""
        has_warn = self.filtered("of_is_account_warn")
        for partner in has_warn:
            partner.of_is_warn = True
        no_warn = self - has_warn
        for partner in no_warn:
            partner.of_is_warn = False

    @api.depends("of_warn_block", "of_is_warn")
    def _compute_invoice_warn(self):
        """Keep this field up to date so that the existing in `account` and `sale` modules continues to work"""
        has_warn = self.filtered("of_is_warn")
        no_warn = self - has_warn
        for partner in no_warn:
            partner.invoice_warn = "no-message"
        for partner in has_warn:
            partner.invoice_warn = "block" if partner.of_warn_block else "warning"
