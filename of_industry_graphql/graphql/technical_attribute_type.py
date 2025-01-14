# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date, datetime

import graphene

from odoo.exceptions import ValidationError


class TechnicalAttributeValue(graphene.Scalar):
    @staticmethod
    def serialize(value):
        if isinstance(value, bool):
            return value
        elif isinstance(value, int):
            return value
        elif isinstance(value, float):
            return value
        elif isinstance(value, str):
            return value
        elif isinstance(value, date):
            return value.isoformat()
        elif isinstance(value, datetime):
            return value.isoformat()
        elif value is None:
            return None
        else:
            raise ValidationError("Cannot represent value as scalar")

    @staticmethod
    def parse_literal(node):
        return node.value

    @staticmethod
    def parse_value(value):
        return value


class TechnicalAttribute(graphene.ObjectType):
    _name = "TechnicalAttribute"
    _type = "types"

    key = graphene.String(required=True)
    value = graphene.Field(TechnicalAttributeValue)


class TechnicalAttributeInput(graphene.InputObjectType):
    _name = "TechnicalAttributeInput"
    _type = "types"

    key = graphene.String()
    value = graphene.Field(TechnicalAttributeValue)
