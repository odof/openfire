# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from datetime import datetime, timedelta

import graphene
import requests

from odoo import http

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain

from .service_request_type import ServiceRequest, ServiceRequestFilterInput


class ServiceRequestQuery(graphene.ObjectType):
    _name = 'ServiceRequestQuery'
    _type = 'query'

    service_requests = graphene.List(
        graphene.NonNull(ServiceRequest),
        filter=graphene.Argument(ServiceRequestFilterInput),
        affectation=graphene.String(),
        sort=graphene.String(),
        period=graphene.String(),
        task=graphene.Int(),
        latitude=graphene.Float(),
        longitude=graphene.Float(),
        max_distance=graphene.Int(),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_service_requests(
        root,
        info,
        filter=None,
        domain=None,
        offset=0,
        limit=10,
        affectation=None,
        sort=None,
        period=None,
        task=None,
        latitude=None,
        longitude=None,
        max_distance=None,
    ):
        env = info.context["env"]
        odoo_domain = []
        odoo_type = {
            'id': 'int',
        }
        if domain:
            odoo_domain = graphqlOdooDomain(odoo_type, domain)

        if filter:
            if filter.id:
                odoo_domain += [('id', '=', filter.id)]
            if filter.name:
                odoo_domain += [('name', 'like', filter.name)]

            if filter.state:
                odoo_domain += [('state', '=', filter.state)]
            if filter.duration:
                odoo_domain += [('duration', '=', filter.duration)]
            if filter.task:
                odoo_domain += [('task', '=', filter.task)]
        if affectation == 'mine':
            # DI affectées au technicien courant
            odoo_domain += [('employee_ids', 'in', [info.context['env'].user.employee_id.id])]
        elif affectation == 'not_affected':
            # DI non affectées à un technicien
            odoo_domain += [('employee_ids', '=', False)]
        elif affectation == 'all':
            # Toutes les DI (affectées et non affectées)
            pass
        if period == "current_week":
            # Semaine en cours : DI dont la période de planification comprend la semaine en cours
            start_of_week = datetime.now().date() - timedelta(days=datetime.now().weekday())
            end_of_week = start_of_week + timedelta(days=6)
            odoo_domain.append(('next_date', '<=', end_of_week))
            odoo_domain.append(('end_date', '>=', start_of_week))
        elif period == "next_week":
            # Semaine prochaine : DI dont la période est planifiée sur la semaine prochaine
            start_of_next_week = datetime.now().date() + timedelta(days=(7 - datetime.now().weekday()))
            end_of_next_week = start_of_next_week + timedelta(days=6)
            odoo_domain.append(('next_date', '>=', start_of_next_week))
            odoo_domain.append(('end_date', '<=', end_of_next_week))
        elif period == "current_month":
            # Mois en cours : DI dont la période de planification comprend le mois en cours
            start_of_month = datetime.now().replace(day=1).date()
            end_of_month = datetime.now().replace(day=1).date() + timedelta(days=31)
            odoo_domain.append(('next_date', '<=', end_of_month))
            odoo_domain.append(('end_date', '>=', start_of_month))
        if latitude is not None and longitude is not None and max_distance is not None:
            max_distance_converted = max_distance / 1000 * 0.621371
            # premier filtre
            domain_states = ['to_plan', 'planned', 'late']
            env.cr.execute(
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
                    longitude,
                    latitude,
                    max_distance_converted,
                    longitude,
                    latitude,
                ),
            )
            result = env.cr.fetchall()
            service_localized_ids = [r[0] for r in result]
            odoo_domain.append(('id', 'in', service_localized_ids))
            service_requests = env['of.service.request'].search(odoo_domain, limit=100)
            user_location = isinstance(latitude, float) and isinstance(longitude, float)
            filter_by_distance = isinstance(max_distance, float) and user_location

            config = env['ir.config_parameter'].sudo()
            if user_location:
                routing_base_url = config.get_param('of_routing_base_url', default='')
                if routing_base_url and service_requests:
                    query = routing_base_url + 'table/v1/driving/' + str(longitude) + "," + str(latitude)
                    # Pour retrouver après envoi les demandes d'interventions
                    # on va se souvenir des index
                    services_index = {}
                    i = 0
                    destinations = ''
                    for service in service_requests:
                        address_localized = service.address_id.partner_longitude and service.address_id.partner_latitude
                        if address_localized:
                            destinations = (
                                destinations
                                + ';'
                                + str(service.address_id.partner_longitude)
                                + ','
                                + str(service.address_id.partner_latitude)
                            )
                            services_index[service.id] = i
                            i = i + 1

                    query = query + destinations + '?sources=0&annotations=distance'
                    req = requests.get(query)
                    res = req.json()

                services_distance = []
                distance_list = []
                if 'distances' in res:
                    distances = res['distances'][0][1:]
                for s in service_requests:
                    distance_index = services_index.get(s.id, None)
                    if distance_index is not None:
                        distance = distances[distance_index]
                        if filter_by_distance and distance > max_distance:
                            continue
                        services_distance.append((s, distance))
                    elif not filter_by_distance:
                        # si aucune distance de calculée, on ne l'inclue que
                        # si on a pas mis de filtre de distance
                        services_distance.append((s, None))
            for s in services_distance:
                distance_list.append(s[0].id)
                odoo_domain.append(('id', 'in', distance_list))
        service_requests_final = env['of.service.request'].search(odoo_domain, offset=offset, limit=limit)
        # Trier les DI
        if sort == 'nearest_end_date':
            service_requests_final = sorted(service_requests_final, key=lambda x: x[0].end_date)
        elif sort == 'nearest_distance':
            service_requests_final = sorted(
                service_requests_final, key=lambda x: float('inf') if x[1] is None else x[1]
            )

        return service_requests_final

    @staticmethod
    # Fonction pour calculer les itinéraires de conduite entre les adresses
    # TODO : test the function with micka
    def find_route_driving(address_paths, info):
        env = info.context["env"]
        config = env['ir.config_parameter'].sudo()
        routing_base_url = config.get_param('of_routing_base_url', default='')
        if not routing_base_url:
            return {'code': 500, 'message': "No routing service", 'session_id': None}
        routing_base_url_driving = routing_base_url + 'route/v1/driving/'

        route_driving_result = []

        for address_path in address_paths:
            partners = http.request.env['res.partner'].search([('id', 'in', address_path)]).sudo()

            if not partners:
                return {'code': 400, 'message': "Empty address path", 'session_id': None}

            partners_sorted = [partners.filtered(lambda p: p.id == address_id) for address_id in address_path]

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
