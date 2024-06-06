# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


import logging

import requests

from odoo import api, fields, models
from odoo.models import expression
from odoo.tools import config

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one, x2many
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain

logger = logging.getLogger(__name__)


class OFServiceRequest(models.Model):
    _inherit = 'of.service.request'

    distance = fields.Float()

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
            mutation['template_id'] = many2one(self=self, model='of.planning.intervention.template', input=template)

        if type := args.get('type'):
            mutation['type_id'] = many2one(self=self, model='of.service.request.type', input=type)

        if 'history_interventions' in args.keys():
            mutation['history_intervention_ids'] = x2many(
                self=self, model='calendar.event', input=args.get('history_interventions')
            )

        if task := args.get('task'):
            mutation['task_id'] = many2one(self=self, model='of.planning.task', input=task)

        if company := args.get('company'):
            mutation['company_id'] = many2one(self=self, model='res.company', input=company)

        if stage := args.get('stage'):
            mutation['stage_id'] = many2one(self=self, model='of.service.request.stage', input=stage)

        if 'employees' in args.keys():
            mutation['employee_ids'] = x2many(self=self, model='hr.employee', input=args.get('employees'))

        if last_attachment := args.get('last_attachment'):
            mutation['last_attachment_id'] = many2one(self=self, model='ir.attachment', input=last_attachment)

        if 'lines' in args.keys():
            mutation['line_ids'] = x2many(self=self, model='of.service.request.line', input=args.get('lines'))

        if partner := args.get('partner'):
            mutation['partner_id'] = many2one(self=self, model='res.partner', input=partner)

        if address := args.get('address'):
            mutation['address_id'] = many2one(self=self, model='res.partner', input=address)

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
            if select.state:
                odoo_domain += [('state', 'in', select.state)]
            if select.duration:
                odoo_domain += [('duration', '=', select.duration)]
            if select.task:
                task_ids = [task.id for task in select.task if task.id]
                if task_ids:
                    odoo_domain += [('task_id', 'in', task_ids)]
            if select.affectation == 'mine':
                # DI affectées au technicien courant
                odoo_domain += [('employee_ids', 'in', [self.env.user.employee_id.id])]
            elif select.affectation == 'not_affected':
                # DI non affectées à un technicien
                odoo_domain += [('employee_ids', '=', False)]
            elif select.affectation == 'all':
                # Toutes les DI (affectées et non affectées)
                pass
            if select.periods:
                periods_domain = []
                for period in select.periods:
                    periods_domain = expression.OR(
                        [
                            periods_domain,
                            [
                                '&',
                                ('next_date', '>=', period.start),
                                ('end_date', '<', period.end),
                            ],
                        ]
                    )
                odoo_domain += periods_domain
            if select.number:
                odoo_domain += [('number', 'ilike', select.number)]
            if select.title:
                odoo_domain += [('title', 'ilike', select.title)]
            if select.address:
                if select.address.name:
                    odoo_domain += [('address_id.name', 'ilike', select.address.name)]
                if select.address.city:
                    odoo_domain += [('address_id.city', 'ilike', select.address.city)]
            if select.query:
                odoo_domain += [
                    '|',
                    '|',
                    '|',
                    ['number', 'ilike', select.query],
                    ['name', 'ilike', select.query],
                    ['address_id.name', 'ilike', select.query],
                    ['address_id.city', 'ilike', select.query],
                ]
            if select.min_duration:
                odoo_domain += [('duration', '>=', select.min_duration)]
            if select.max_duration:
                odoo_domain += [('duration', '<=', select.max_duration)]
            if select.task_duration == "one_hour":
                odoo_domain += [('duration', '<=', 1.0)]
            if select.task_duration == "two_hours":
                odoo_domain += [('duration', '<=', 2.0), ('duration', '>', 1.0)]
            if select.task_duration == "four_hours":
                odoo_domain += [('duration', '<=', 4.0), ('duration', '>', 2.0)]
            if select.task_duration == "four_hours_more":
                odoo_domain += [('duration', '>', 4.0)]
            if select.latitude is not None and select.longitude is not None and select.max_distance is not None:
                max_distance_converted = select.max_distance / 1000 * 0.621371
                # premier filtre
                domain_states = ['to_plan', 'draft', 'planned', 'late']
                self.env.cr.execute(
                    """select service.id
                        from of_service_request service
                        LEFT JOIN res_partner partner
                            ON partner.id = service.address_id
                        where service.address_id is not null and
                        service.state in %s and
                        (partner.partner_longitude != 0 and partner.partner_latitude != 0) and
                        float8 (point(partner.partner_longitude,partner.partner_latitude) <@> point(%s, %s)) < %s
                        ORDER BY point(partner.partner_longitude,partner.partner_latitude) <@> point(%s, %s);
                        """,
                    (
                        tuple(domain_states),
                        select.longitude,
                        select.latitude,
                        max_distance_converted,
                        select.longitude,
                        select.latitude,
                    ),
                )
                result = self.env.cr.fetchall()
                service_localized_ids = [r[0] for r in result]
                odoo_domain.append(('id', 'in', service_localized_ids))
                service_requests = self.env['of.service.request'].search(odoo_domain, limit=100)
                services_distance = self.calculate_distances(
                    service_requests, select.latitude, select.longitude, max_distance_converted
                )
                for s in services_distance:
                    for service in service_requests:
                        if s[0].id == service.id:
                            service.distance = s[1]
                distance_list = [s[0].id for s in services_distance]
                odoo_domain.append(('id', 'in', distance_list))

        return odoo_domain

    def calculate_distances(self, service_requests, latitude, longitude, max_distance):
        routing_base_url = config.get('of_routing_base_url', default='')
        services_index = {}
        destinations = ''
        for i, service in enumerate(service_requests):
            address_localized = service.address_id.partner_longitude and service.address_id.partner_latitude
            if address_localized:
                destinations += f";{service.address_id.partner_longitude},{service.address_id.partner_latitude}"
                services_index[service.id] = i

        query = (
            f"{routing_base_url}table/v1/driving/{longitude},{latitude}{destinations}?sources=0&annotations=distance"
        )
        req = requests.get(query)
        res = req.json()
        distances = res.get('distances', [[]])[0][1:]
        services_distance = []
        for service in service_requests:
            distance_index = services_index.get(service.id)
            if distance_index is not None:
                distance = distances[distance_index]
                if max_distance is not None and distance > max_distance:
                    services_distance.append((service, distance))
        return services_distance

    # Fonction pour calculer les itinéraires de conduite entre les adresses
    # TODO : test the function with micka and check if we still need this function or not
    def find_route_driving(self, address_paths):
        config = self.env['ir.config_parameter'].sudo()
        routing_base_url = config.get_param('of_routing_base_url', default='')
        if not routing_base_url:
            return {'code': 500, 'message': "No routing service", 'session_id': None}
        routing_base_url_driving = routing_base_url + 'route/v1/driving/'

        route_driving_result = []

        for address_path in address_paths:
            partners = self.env['res.partner'].search([('id', 'in', address_path)]).sudo()

            if not partners:
                return {'code': 400, 'message': "Empty address path", 'session_id': None}

            partners_sorted = [partners.selected(lambda p: p.id == address_id) for address_id in address_path]

            query = routing_base_url_driving

            lng = partners_sorted[0].partner_longitude
            lat = partners_sorted[0].partner_latitude
            query = query + str(lng) + ',' + str(lat)

            for partner in partners_sorted[1:]:
                lng = partner.partner_longitude
                lat = partner.partner_latitude
                query = query + ';' + str(lng) + ',' + str(lat)

            query += '?overview=full&steps=true'
            req = requests.get(query)
            res = req.json()

            legs = res['routes'][0]['legs']

            steps_result = []

            for leg in legs:
                steps = leg['steps']
                for step in steps:
                    intersections = step['intersections']
                    for intersection in intersections:
                        location = intersection['location']
                        steps_result.append({'longitude': location[0], 'latitude': location[1]})

            route_driving_result.append(
                {
                    'steps': steps_result,
                    'address_path': address_path,
                }
            )

        return route_driving_result
