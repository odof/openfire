# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene


class GeoLocalizedAddress(graphene.ObjectType):
    _name = 'GeoLocalizedAddress'
    _type = 'types'

    def __init__(self, longitude, latitude):
        self.longitude = longitude
        self.latitude = latitude

    longitude = graphene.Float(required=True)
    latitude = graphene.Float(required=True)
