# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene


class TechnicalAttributeType(graphene.Enum):
    BOOLEAN = "boolean"
    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    DATE = "date"
    DATETIME = "datetime"
    SELECTION = "selection"
    MANY2ONE_ID = "many2one_id"


class TechnicalAttributeSchema(graphene.ObjectType):
    _name = "TechnicalAttributeSchema"
    _type = "types"

    def __init__(self, name, key, required, ttype, readonly):
        self.name = name
        self.key = key
        self.required = required
        self.ttype = ttype
        self.readonly = readonly

    name = graphene.String(required=True)
    key = graphene.String(required=True)
    required = graphene.Boolean(required=True)
    ttype = graphene.Field(TechnicalAttributeType, required=True)
    readonly = graphene.Boolean(required=True)
