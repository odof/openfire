# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene


class PartnerCheckDuplications(graphene.InputObjectType):
    _name = 'PartnerCheckDuplications'
    _type = 'types'

    email = graphene.String()
    phone_numbers = graphene.List(graphene.NonNull(graphene.String))
