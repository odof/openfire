import logging

import graphene

logger = logging.getLogger(__name__)


class OdooImage(graphene.Scalar):
    @staticmethod
    def serialize(value):
        value = value.decode("utf-8")
        return value

    @staticmethod
    def parse_literal(ast):
        logger.info("parse_literal")
        return ast.value

    @staticmethod
    def parse_value(value):
        logger.info("parse_value")
        return value


def graphqlOdooDomain(odoo_type, domain):
    """Permet de transformer un domain graphql en domain odoo
    Le champs odoo_type doit contenir un dictionnaire qui associe les champs qui ne sont pas des str
    A leur type (int, float etc.)
    Car la valeur qui est dans le domain graphql est forcément un str, donc on doit le convertir
    avant de le passer à odoo
    """

    odoo_domain = []
    for d in domain:
        field = d.field
        operator = d.operator.value
        value = d.value

        if field in odoo_type:
            if odoo_type[field] == 'int':
                if operator in ["in", "not in"]:
                    value = d.value.replace("[", "").replace("]", "")
                    value = value.split(",")
                    value = [int(v) for v in value]
                else:
                    value = int(d.value)
            elif odoo_type[field] == 'float':
                if operator in ["in", "not in"]:
                    value = d.value.replace("[", "").replace("]", "")
                    value = value.split(",")
                    value = [float(v) for v in value]
                else:
                    value = float(d.value)
            elif odoo_type[field] == 'boolean':
                if operator in ["in", "not in"]:
                    value = d.value.replace("[", "").replace("]", "")
                    value = value.split(",")
                    value = [bool(v) for v in value]
                else:
                    value = bool(d.value)
            else:
                if operator in ["in", "not in"]:
                    value = d.value.replace("[", "").replace("]", "")
                    value = value.split(",")

        odoo_domain += [(field, operator, value)]
    return odoo_domain
