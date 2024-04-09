# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models

from odoo.addons.of_graphql.graphql.odoo_graphql import convertImage, many2one, x2many
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        if state := args.get('state'):
            mutation['of_state'] = state

        if duration := args.get('duration'):
            mutation['duration'] = duration

        if start := args.get('start'):
            mutation['start'] = start

        if stop := args.get('stop'):
            mutation['stop'] = stop

        if real_start := args.get('real_start'):
            mutation['of_real_start'] = real_start

        if real_stop := args.get('real_stop'):
            mutation['of_real_stop'] = real_stop

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

        if real_duration := args.get('real_duration'):
            mutation['of_real_duration'] = real_duration

        if task := args.get('task'):
            mutation['of_task_id'] = many2one(self=self, model="of.planning.task", input=task)

        if ttype := args.get('type'):
            mutation['of_type_id'] = many2one(self=self, model="of.service.request", input=ttype)

        if internal_description := args.get('internal_description'):
            mutation['of_internal_description'] = internal_description

        if external_description := args.get('external_description'):
            mutation['description'] = external_description

        if minutes := args.get('minutes'):
            mutation['of_minutes'] = minutes

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

        if args.get('origin', False) == "mobile":
            mutation['of_force_dates'] = True
            mutation['user_id'] = self.env.user.id
            # Par défaut le mobile ne créera que des interventions
            mutation['of_type'] = 'intervention'

        if partner := args.get('partner'):
            mutation['of_partner_id'] = many2one(self=self, model="res.partner", input=partner)

        if address := args.get('address'):
            mutation['of_address_id'] = many2one(self=self, model="res.partner", input=address)

        if 'invoices' in args:
            mutation['of_invoice_ids'] = x2many(self=self, model="account.move", input=args.get('invoices'))

        if 'invoice_lines' in args:
            mutation['of_line_ids'] = x2many(
                self=self, model='of.planning.intervention.line', input=args.get('invoice_lines')
            )

        if 'pickings' in args:
            mutation['of_picking_ids'] = x2many(self=self, model="stock.picking", input=args.get('pickings'))

        if 'manual_pickings' in args:
            mutation['of_picking_manual_ids'] = x2many(
                self=self, model="stock.picking", input=args.get('manual_pickings')
            )

        if 'images' in args:
            mutation['of_all_image_ids'] = x2many(self=self, model="of.image", input=args.get('images'))

        if order := args.get('order'):
            mutation['of_order_id'] = many2one(self=self, model='sale.order', input=order)

        if template := args.get('template'):
            mutation['of_template_id'] = many2one(self=self, model='of.planning.intervention.template', input=template)

        if 'employees' in args:
            mutation['of_employee_ids'] = x2many(self=self, model='hr.employee', input=args.get('employees'))

        if company := args.get('company'):
            mutation['of_company_id'] = many2one(self=self, model='res.company', input=company)

        if 'tags' in args:
            mutation['of_tag_ids'] = x2many(self=self, model='of.planning.tag', input=args.get('tags'))

        if service_request := args.get('service_request'):
            mutation['of_request_id'] = many2one(self=self, model='of.service.request', input=service_request)

        return mutation

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = []

        if domain:
            odoo_domain = graphqlOdooDomain(self=self, model='calendar.event', domain=domain)

        if select:
            today = fields.Date.from_string(fields.Date.today())

            if select.id:
                odoo_domain += [('id', '=', select.id)]
            if select.name:
                odoo_domain += [('name', 'ilike', select.name)]
            if select.duration:
                odoo_domain += [('duration', '=', select.duration)]
            if select.start:
                odoo_domain += [('start', '=', select.start)]
            if select.stop:
                odoo_domain += [('stop', '=', select.stop)]
            if select.days_before_today:
                before = today + relativedelta(days=-select.days_before_today)
                odoo_domain += [('start', '>=', fields.Date.to_string(before))]
            if select.days_after_today:
                after = today + relativedelta(days=-select.days_after_today)
                odoo_domain += [('start', '>=', fields.Date.to_string(after))]
            odoo_domain += [('of_state', 'not in', ['cancel', 'postponed']), ('of_type', '=', 'intervention')]

        return odoo_domain
