# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    of_intervention_id = fields.Many2one(comodel_name="calendar.event", string="Intervention")
    of_intervention_invoice_id = fields.Many2one(comodel_name="account.move", string="Intervention Invoice")
    of_sale_id = fields.Many2one(comodel_name="sale.order", string="Sale Order")
    of_sale_invoice_id = fields.Many2one(comodel_name="account.move", string="Sale Invoice")
    of_type = fields.Selection(
        [("all", "All"), ("intervention", "Intervention"), ("sale", "Sale"), ("none", "None")],
        default="none",
        string="Type (OF)",
    )

    @api.model
    def create_payment_intervention(self, intervention, amount, ttype, mode, date=False, partner=False):
        """
        Create a payment for an intervention.

        Args:
            intervention (calendar.event): The intervention for which the payment is being created.
            amount (float): The amount of the payment.
            ttype (str): The type of the payment. Possible values are 'sale' and 'all'.
            mode (of.payment.mode): The payment mode.
            date (bool, optional): The payment date. Defaults to False. If False, the current date is used.
            partner (res.partner, optional): The partner for the payment. Defaults to False.
                If False, the partner of the intervention is used.

        Returns:
            account.payment: The created payment object or an empty recordset if there are no invoices to pay.
        """
        invoices = self.env["account.move"].browse()
        sale = False
        sale_invoice = False
        intervention_invoice = False
        mode = self.env["of.payment.mode"].browse(mode.id)
        ttype = ttype._value_
        intervention = self.env["calendar.event"].browse(intervention.id)

        if not date:
            date = fields.Datetime.now()

        if (
            intervention.of_line_ids
            and intervention.of_template_id
            and intervention.of_template_id.mobile_payment
            and ttype in ["intervention", "all"]
        ):
            intervention_invoice = intervention.action_mobile_create_invoice()
            if intervention.of_template_id.auto_confirm_invoice:
                intervention_invoice.action_post()
            invoices += intervention_invoice

        if ttype in ["sale", "all"]:
            if sale := intervention.of_additional_sale_order_id:
                sale_invoice = sale._create_invoices()

                if intervention.of_template_id and intervention.of_template_id.auto_confirm_invoice:
                    sale_invoice.action_post()
                invoices += sale_invoice

        if not partner:
            partner = intervention.of_partner_id
        else:
            partner = self.env["res.partner"].browse(partner.id)

        # si jamais une facture n'est pas en état "posted", on doit faire un paiement non lettré
        # à la facture
        payments = self.env["account.payment"].browse()
        if non_posted_invoices := invoices.filtered(lambda i: i.state != "posted"):
            value_payment = {
                "amount": amount,
                "date": date,
                "partner_id": partner.id,
                "of_payment_mode_id": mode.id,
                "of_intervention_id": intervention.id,
                "of_type": ttype,
            }
            if intervention_invoice:
                value_payment["of_intervention_invoice_id"] = intervention_invoice.id
            if sale:
                value_payment["of_sale_id"] = sale.id
            if sale_invoice:
                value_payment["of_sale_invoice_id"] = sale_invoice.id
            payment = self.env["account.payment"].create(value_payment)
            payment.action_post()
            payments += payment
            invoices -= non_posted_invoices

        if not invoices:
            # il ne reste plus de factures "posted", donc on retourne les paiements
            # ou alors il n'y a pas eu du tout de factures
            return payments

        register_payments = (
            self.env["account.payment.register"]
            .with_context(
                active_model="account.move",
                active_ids=invoices.ids,
                default_journal_id=mode.journal_id.id,
                default_partner_id=partner.id,
                default_amount=amount,
                default_payment_date=date,
            )
            .create({"group_payment": True})
        )
        payment = register_payments._create_payments()

        # Update the payment with the intervention and additional sale order information
        payment.of_intervention_id = intervention.id
        payment.of_type = ttype
        if intervention_invoice:
            payment.of_intervention_invoice_id = intervention_invoice.id
        if sale:
            payment.of_sale_id = sale.id
        if sale_invoice:
            payment.of_sale_invoice_id = sale_invoice.id
        return payment
