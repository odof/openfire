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
        return ast.value

    @staticmethod
    def parse_value(value):
        return value


def graphqlOdooDomain(self, model, domain):
    """Permet de transformer un domain graphql en domain odoo"""
    odoo_domain = []
    odoo_type = {}
    odoo_model = self.env['ir.model'].search([('model', '=', model)])
    for d in domain:
        field = d.field

        # on va chercher dans odoo le type du champs
        odoo_field = self.env['ir.model.fields'].search([('model_id', '=', odoo_model.id), ('name', '=', field)])

        operator = d.operator.value
        value = d.value

        if field in odoo_type:
            if odoo_field.ttype == 'integer':
                if operator in ["in", "not in"]:
                    value = d.value.replace("[", "").replace("]", "")
                    value = value.split(",")
                    value = [int(v) for v in value]
                else:
                    value = int(d.value)
            elif odoo_field.ttype == 'float':
                if operator in ["in", "not in"]:
                    value = d.value.replace("[", "").replace("]", "")
                    value = value.split(",")
                    value = [float(v) for v in value]
                else:
                    value = float(d.value)
            elif odoo_field.ttype == 'boolean':
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
