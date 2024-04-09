# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene


class PartnerCheckDuplications(graphene.InputObjectType):
    _name = 'PartnerCheckDuplications'
    _type = 'types'

    email = graphene.String()
    phone_numbers = graphene.List(graphene.NonNull(graphene.String))
