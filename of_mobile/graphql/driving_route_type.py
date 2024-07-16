# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_base_graphql.graphql.partner_type import Partner


class DrivingRouteCoordinates(graphene.ObjectType):
    _name = 'DrivingRouteCoordinates'
    _type = 'types'

    def __init__(self, longitude, latitude):
        self.longitude = longitude
        self.latitude = latitude

    longitude = graphene.Float(required=True)
    latitude = graphene.Float(required=True)


class DrivingRouteStop(graphene.ObjectType):
    _name = 'DrivingRouteStop'
    _type = 'types'

    def __init__(self, duration, distance, partner):
        self.duration = duration
        self.distance = distance
        self.partner = partner

    duration = graphene.Float()
    distance = graphene.Float()
    partner = graphene.Field(Partner, required=True)


class DrivingRoutePath(graphene.ObjectType):
    _name = 'DrivingRoutePath'
    _type = 'types'

    stops = graphene.List(graphene.NonNull(DrivingRouteStop), required=True)
    coordinates = graphene.List(graphene.NonNull(DrivingRouteCoordinates), required=True)


class DrivingRoute(graphene.ObjectType):
    _name = 'DrivingRoute'
    _type = 'types'

    paths = graphene.List(graphene.NonNull(DrivingRoutePath), required=True)
