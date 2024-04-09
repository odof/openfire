import graphene


class OdooOperator(graphene.Enum):
    EQ = "="
    LIKE = "ilike"
    GT = ">"
    GT_EQ = ">="
    LT = "<"
    LT_EQ = "<="
    NOT = "!="
    IN = "in"
    NOT_IN = "not in"


class OdooFields(graphene.Scalar):
    @staticmethod
    def serialize(value):
        return value

    @staticmethod
    def parse_literal(ast):
        return ast.value

    @staticmethod
    def parse_value(value):
        return value


class OdooDomainInput(graphene.InputObjectType):
    field = graphene.Field(OdooFields, odoo_fields=graphene.List(graphene.String))
    operator = graphene.Field(OdooOperator)
    value = graphene.String()

    @staticmethod
    def resolve_field(root, info, odoo_fields):
        return odoo_fields
