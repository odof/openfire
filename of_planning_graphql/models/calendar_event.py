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

        if 'invoices' in args.keys():
            mutation['of_invoice_ids'] = x2many(self=self, model="account.move", input=args.get('invoices'))

        if 'invoice_lines' in args.keys():
            mutation['of_line_ids'] = x2many(
                self=self, model='of.planning.intervention.line', input=args.get('invoice_lines')
            )

        if 'pickings' in args.keys():
            mutation['picking_ids'] = x2many(self=self, model="stock.picking", input=args.get('pickings'))

        if 'images' in args.keys():
            mutation['of_all_image_ids'] = x2many(self=self, model="of.image", input=args.get('images'))

        if order := args.get('order'):
            mutation['order_id'] = many2one(self=self, model='sale.order', input=order)

        if template := args.get('template'):
            mutation['of_template_id'] = many2one(self=self, model='of.planning.intervention.template', input=template)

        if 'employees' in args.keys():
            mutation['of_employee_ids'] = x2many(self=self, model='hr.employee', input=args.get('employees'))

        if company := args.get('company'):
            mutation['company_id'] = many2one(self=self, model='res.company', input=company)

        if 'tags' in args.keys():
            mutation['of_tag_ids'] = x2many(self=self, model='of.planning.tag', input=args.get('tags'))

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
