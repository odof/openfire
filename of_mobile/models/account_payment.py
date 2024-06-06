# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, fields, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    intervention_id = fields.Many2one(comodel_name='calendar.event', string="Intervention")
    intervention_invoice_id = fields.Many2one(comodel_name='account.move', string="Intervention Invoice")

    @api.model_create_multi
    def create(self, vals_list):
        # si on a une intervention de renseignée, c'est que l'on paye l'intervention associée
        # donc on va aussi lancer la facturation de cette intervention
        for vals in vals_list:
            if intervention_id := vals.get('intervention_id'):
                intervention = self.env['calendar.event'].browse(intervention_id)
                if intervention.of_template_id and intervention.of_template_id.mobile_payment:
                    invoice = intervention.action_mobile_create_invoice()
                    vals['intervention_invoice_id'] = invoice.id
                    if intervention.of_template_id and intervention.of_template_id.auto_confirm_invoice:
                        invoice.action_post()

        return super().create(vals_list)

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = super()._prepare_mutation_values(**args)

        if intervention := args.get('intervention'):
            mutation['intervention_id'] = many2one(self=self, model='calendar.event', input=intervention)

        return mutation
