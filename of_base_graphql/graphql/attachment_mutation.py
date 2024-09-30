# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_type import OdooImage

from .attachment_type import Attachment, AttachmentType


def convertImage(datas):
    datas = datas.split(",")
    datas = datas[1] if len(datas) > 1 else datas[0]
    return datas


class AttachmentCreate(graphene.Mutation):
    _name = "AttachmentCreate"

    class Arguments:
        name = graphene.String(required=True)
        type = graphene.Argument(AttachmentType)
        res_model = graphene.String(name="model")
        res_id = graphene.Int(name="model_id")
        datas = OdooImage()

    Output = Attachment

    def mutate(self, info, **args):
        env = info.context["env"]
        values = env["ir.attachment"]._prepare_mutation_values(**args)
        return env["ir.attachment"].create(values)


class AttachmentUpdate(graphene.Mutation):
    _name = "AttachmentUpdate"

    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String(required=True)
        type = graphene.Argument(AttachmentType)
        res_model = graphene.String(name="model")
        res_id = graphene.Int(name="model_id")
        datas = OdooImage()

    Output = Attachment

    def mutate(self, info, id, **args):
        env = info.context["env"]
        values = env["ir.attachment"]._prepare_mutation_values(**args)
        attachment = env["ir.attachment"].search([("id", "=", id)])
        attachment.write(values)
        return attachment


class AttachmentMutation(graphene.ObjectType):
    _name = "AttachmentMutation"
    _type = "mutation"

    attachment_create = AttachmentCreate.Field()
    attachment_update = AttachmentUpdate.Field()
