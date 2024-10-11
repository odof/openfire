# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene
import requests

from odoo.tools import config

from .driving_route_type import DrivingRoute, DrivingRouteCoordinates, DrivingRoutePath, DrivingRouteStop


class DrivingRouteQuery(graphene.ObjectType):
    _name = "DrivingRouteQuery"
    _type = "query"

    driving_route = graphene.Field(
        DrivingRoute,
        description="Retourne le trajet GPS pour une ou plusieurs listes de partners",
        partner_paths_ids=graphene.List(
            graphene.NonNull(
                graphene.List(graphene.NonNull(graphene.Int, required=True)),
            ),
            required=True,
        ),
    )

    @staticmethod
    def resolve_driving_route(root, info, partner_paths_ids):
        env = info.context["env"]

        routing_base_url = config.get("of_routing_base_url", default="")
        if not routing_base_url.endswith("/"):
            routing_base_url += "/"
        routing_base_url_driving = f"{routing_base_url}route/v1/driving/"

        driving_route = DrivingRoute()
        driving_route.paths = []

        for partner_path_ids in partner_paths_ids:
            partners = env["res.partner"].search([("id", "in", partner_path_ids)]).sudo()

            if not partners:
                continue

            if len(partners) != len(partner_path_ids) or len(partners) == 1:
                continue

            # Ensure the sequence by ordering the list according to the input partner id list
            partners_sorted = [next(filter(lambda x: x.id == partner_id, partners)) for partner_id in partner_path_ids]

            lng = partners_sorted[0].partner_longitude
            lat = partners_sorted[0].partner_latitude
            query = f"{routing_base_url_driving}{str(lng)},{str(lat)}"  # noqa E231

            for partner in partners_sorted[1:]:
                lng = partner.partner_longitude
                lat = partner.partner_latitude
                query = f"{query};{str(lng)},{str(lat)}"  # noqa E231

            query += "?overview=full&steps=true"
            req = requests.get(query, timeout=10)
            res = req.json()

            legs = res["routes"][0]["legs"]

            coordinates = []
            # there is necessarly no duration  and distance to the first partner
            stops = [DrivingRouteStop(None, None, partners_sorted[0])]
            for partner_index, leg in enumerate(legs, start=1):
                steps = leg["steps"]
                distance = leg["distance"]
                duration = leg["duration"]
                stops.append(DrivingRouteStop(distance, duration, partners_sorted[partner_index]))
                for step in steps:
                    intersections = step["intersections"]
                    for intersection in intersections:
                        location = intersection["location"]
                        coordinates.append(DrivingRouteCoordinates(location[0], location[1]))

            driving_route_path = DrivingRoutePath()
            driving_route_path.coordinates = coordinates
            driving_route_path.stops = stops

            driving_route.paths.append(driving_route_path)

        return driving_route
