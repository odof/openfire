# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    of_customer_state = fields.Selection(related='partner_id.of_customer_state', required=False)

    @api.onchange('partner_id')
    def _onchange_partner_id_warning(self):
        if not (partner := self.partner_id):
            return
        # If partner has no warning, check its parents
        # invoice_warn is shared between different objects
        if not partner.of_is_lead_warn and partner.parent_id:
            partner = partner.parent_id

        if partner.of_is_lead_warn and partner.invoice_warn != 'no-message':
            if partner.invoice_warn != 'block' and partner.parent_id and partner.parent_id.invoice_warn == 'block':
                partner = partner.parent_id
            warning = {'title': _("Warning for %s") % partner.name, 'message': partner.invoice_warn_msg}
            if partner.invoice_warn == 'block':
                self.partner_id = False
            return {'warning': warning}

    def _prepare_opportunity_quotation_context(self):
        quotation_context = super()._prepare_opportunity_quotation_context()
        quotation_context['default_of_referred_id'] = self.of_referred_id.id
        return quotation_context
