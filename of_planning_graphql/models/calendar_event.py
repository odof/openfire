# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import convertImage, many2one, x2many


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        if duration := args.get('duration'):
            mutation['duration'] = duration

        if start := args.get('start'):
            mutation['start'] = start

        if stop := args.get('stop'):
            mutation['stop'] = stop

        if days_before_today := args.get('days_before_today'):
            mutation['days_before_today'] = days_before_today

        if days_after_today := args.get('days_after_today'):
            mutation['days_after_today'] = days_after_today

        if total_duration := args.get('total_duration'):
            mutation['of_total_duration'] = total_duration

        if break_duration := args.get('break_duration'):
            mutation['of_break_duration'] = break_duration

        if travel_duration := args.get('travel_duration'):
            mutation['of_travel_duration'] = travel_duration

        if task := args.get('task'):
            mutation['of_state'] = task

        if type := args.get('type'):
            mutation['of_type'] = type

        if internal_description := args.get('internal_description'):
            mutation['of_internal_description'] = internal_description

        if intervention_notes := args.get('intervention_notes'):
            mutation['of_intervention_notes'] = intervention_notes

        if customer_notes := args.get('customer_notes'):
            mutation['of_customer_notes'] = customer_notes

        # Les données qui viennent de cet input (dans datas) doivent être modifiées avant d'être
        # importé dans odoo, donc on convertit à la volée
        if attachment := args.get("customer_signature", False):
            mutation['of_customer_signature'] = convertImage(attachment)

        if attachment := args.get("operator_signature", False):
            mutation['of_operator_signature'] = convertImage(attachment)

        if args.get('origin', False) == "MOBILE":
            mutation['of_force_dates'] = True
            mutation['name'] = ''
            mutation['user_id'] = self.env.user.id
            mutation['last_updated_mobile'] = True

        if partner := args.get('partner'):
            mutation['of_partner_id'] = many2one(self=self, model="res.partner", input=partner)

        if invoices := args.get('invoices'):
            mutation['of_invoice_ids'] = x2many(self=self, model="account.move", input=invoices)

        if pickings := args.get('pickings'):
            mutation['picking_ids'] = x2many(self=self, model="stock.picking", input=pickings)

        if images := args.get('images'):
            mutation['of_all_image_ids'] = x2many(self=self, model="ir.attachment", input=images)

        if order := args.get('order'):
            mutation['order_id'] = many2one(self=self, model='sale.order', input=order)

        if template := args.get('template'):
            mutation['of_template_id'] = many2one(self=self, model='of.planning.intervention.template', input=template)

        if employees := args.get('employees'):
            mutation['of_employee_ids'] = x2many(self=self, model='hr.employee', input=employees)

        if company := args.get('company'):
            mutation['company_id'] = many2one(self=self, model='res.company', input=company)

        return mutation
