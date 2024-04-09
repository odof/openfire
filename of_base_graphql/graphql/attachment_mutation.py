import logging

import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_update

from .attachment_type import Attachment, AttachmentCreateInput, AttachmentUpdateInput

logger = logging.getLogger(__name__)


def convertImage(datas):
    datas = datas.split(",")
    if len(datas) > 1:
        datas = datas[1]
    else:
        datas = datas[0]
    return datas


class AttachmentCreate(graphene.Mutation):
    _name = 'AttachmentCreate'

    class Arguments:
        input = AttachmentCreateInput(required=True)

    Output = Attachment

    def mutate(self, info, input):
        env = info.context["env"]
        # Les données qui viennent de cet input (dans datas) doivent être modifiées avant d'être
        # importé dans odoo, donc on convertit à la volée
        if attachment := input.get("datas", False):
            input.datas = convertImage(attachment)

        return lazy_create(env, "ir.attachment", input)


class AttachmentUpdate(graphene.Mutation):
    _name = 'AttachmentUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = AttachmentUpdateInput(required=True)

    Output = Attachment

    def mutate(self, info, id, input):
        env = info.context["env"]
        # Les données qui viennent de cet input (dans datas) doivent être modifiées avant d'être
        # importé dans odoo, donc on convertit à la volée
        if attachment := input.get("datas", False):
            input.datas = convertImage(attachment)
        return lazy_update(env, "ir.attachment", id, input)


class AttachmentMutation(graphene.ObjectType):
    _name = 'AttachmentMutation'
    _type = 'mutation'

    attachment_create = AttachmentCreate.Field()
    attachment_update = AttachmentUpdate.Field()
