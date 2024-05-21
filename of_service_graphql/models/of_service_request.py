# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta

import requests

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
            if select.state:
                odoo_domain += [('state', '=', select.state)]
            if select.duration:
                odoo_domain += [('duration', '=', select.duration)]
            if select.task:
                odoo_domain += [('task', '=', select.task)]
            if select.affectation == 'mine':
                # DI affectées au technicien courant
                odoo_domain += [('employee_ids', 'in', [self.env.user.employee_id.id])]
            elif select.affectation == 'not_affected':
                # DI non affectées à un technicien
                odoo_domain += [('employee_ids', '=', False)]
            elif select.affectation == 'all':
                # Toutes les DI (affectées et non affectées)
                pass
            if select.period == "current_week":
                # Semaine en cours : DI dont la période de planification comprend la semaine en cours
                start_of_week = datetime.now().date() - timedelta(days=datetime.now().weekday())
                end_of_week = start_of_week + timedelta(days=6)
                odoo_domain.append(('next_date', '<=', end_of_week))
                odoo_domain.append(('end_date', '>=', start_of_week))
            elif select.period == "next_week":
                # Semaine prochaine : DI dont la période est planifiée sur la semaine prochaine
                start_of_next_week = datetime.now().date() + timedelta(days=(7 - datetime.now().weekday()))
                end_of_next_week = start_of_next_week + timedelta(days=6)
                odoo_domain.append(('next_date', '>=', start_of_next_week))
                odoo_domain.append(('end_date', '<=', end_of_next_week))
            elif select.period == "current_month":
                # Mois en cours : DI dont la période de planification comprend le mois en cours
                start_of_month = datetime.now().replace(day=1).date()
                end_of_month = datetime.now().replace(day=1).date() + timedelta(days=31)
                odoo_domain.append(('next_date', '<=', end_of_month))
                odoo_domain.append(('end_date', '>=', start_of_month))
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
                distance_list = [s[0].id for s in services_distance]
                odoo_domain.append(('id', 'in', distance_list))

        return odoo_domain

    def calculate_distances(self, service_requests, latitude, longitude, max_distance):
        config = self.env['ir.config_parameter'].sudo()
        routing_base_url = config.get_param('of_routing_base_url', default='')
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
