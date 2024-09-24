# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from .geo_localize_address_type import GeoLocalizedAddress


class GeoLocalizeAddressQuery(graphene.ObjectType):
    _name = 'GeoLocalizeAddressQuery'
    _type = 'query'

    geo_localize_address = graphene.Field(
        GeoLocalizedAddress,
        description="Retourne la position GPS d'une adresse, celle-ci peut être nulle si non trouvée",
        street=graphene.String(),
        zip=graphene.String(),
        city=graphene.String(),
        state=graphene.String(),
        country=graphene.String(),
    )

    @staticmethod
    def resolve_geo_localize_address(root, info, street='', zip='', city='', state='', country=''):
        env = info.context['env']

        geo_obj = env['base.geocoder']
        search = geo_obj.geo_query_address(street=street, zip=zip, city=city, state=state, country=country)
        result = geo_obj.geo_find(search, force_country=country)

        return GeoLocalizedAddress(longitude=result[1], latitude=result[0]) if result else None
