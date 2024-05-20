# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one, x2many
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain


class OFServiceRequest(models.Model):
    _inherit = 'of.service.request'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        if 'active' in args.keys():
            mutation['active'] = args['active']

        if origin := args.get('origin'):
            mutation['origin'] = origin

        if number := args.get('number'):
            mutation['number'] = number

        if title := args.get('title'):
            mutation['title'] = title

        if priority := args.get('priority'):
            mutation['priority'] = priority

        if date := args.get('date'):
            mutation['request_label_date'] = date

        if planning_status := args.get('planning_status'):
            mutation['state'] = planning_status

        if calculation_status := args.get('calculation_status'):
            mutation['base_state'] = calculation_status

        if state := args.get('state'):
            mutation['state_punctual'] = state

        if 'interventions' in args.keys():
            mutation['intervention_ids'] = x2many(self=self, model='calendar.event', input=args.get('interventions'))

        if intervention_count := args.get('intervention_count'):
            mutation['intervention_count'] = intervention_count

        if template := args.get('template'):
            mutation['template'] = many2one(self=self, model='of.planning.intervention.template', input=template)

        if type := args.get('type'):
            mutation['type'] = many2one(self=self, model='of.service.request.type', input=type)

        if 'history_interventions' in args.keys():
            mutation['history_intervention_ids'] = x2many(
                self=self, model='calendar.event', input=args.get('history_interventions')
            )

        if task := args.get('task'):
            mutation['task'] = many2one(self=self, model='of.planning.task', input=task)

        if company := args.get('company'):
            mutation['company_id'] = many2one(self=self, model='res.company', input=company)

        if stage := args.get('stage'):
            mutation['stage'] = many2one(self=self, model='of.service.request.stage', input=stage)

        if 'employees' in args.keys():
            mutation['employee_ids'] = x2many(self=self, model='hr.employee', input=args.get('employees'))

        if last_attachment := args.get('last_attachment'):
            mutation['last_attachment'] = many2one(self=self, model='ir.attachment', input=last_attachment)

        if 'lines' in args.keys():
            mutation['line_ids'] = x2many(self=self, model='of.service.request.line', input=args.get('lines'))

        if partner := args.get('partner'):
            mutation['partner'] = many2one(self=self, model='res.partner', input=partner)

        if address := args.get('address'):
            mutation['address'] = many2one(self=self, model='res.partner', input=address)

        if next_date := args.get('next_date'):
            mutation['next_date'] = next_date

        if end_date := args.get('end_date'):
            mutation['end_date'] = end_date

        if contract_end_date := args.get('contract_end_date'):
            mutation['contract_end_date'] = contract_end_date

        if duration := args.get('duration'):
            mutation['duration'] = duration

        if planned_duration := args.get('planned_duration'):
            mutation['planned_duration'] = planned_duration

        if remaining_duration := args.get('remaining_duration'):
            mutation['remaining_duration'] = remaining_duration

        return mutation

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = []

        if domain:
            odoo_domain = graphqlOdooDomain(self=self, model='of.service.request', domain=domain)

        if select:
            if select.id:
                odoo_domain += [('id', '=', select.id)]
            if select.name:
                odoo_domain += [('name', 'like', select.name)]

        return odoo_domain
