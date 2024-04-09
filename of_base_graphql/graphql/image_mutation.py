# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete
from odoo.addons.of_graphql.graphql.odoo_type import OdooImage

from .image_type import Image


class ImageCreate(graphene.Mutation):
    _name = 'ImageCreate'

    class Arguments:
        name = graphene.String()
        caption = graphene.String()
        sequence = graphene.Int()
        printable = graphene.Boolean()
        image_1920 = OdooImage()

    Output = Image

    def mutate(self, info, **args):
        env = info.context['env']
        values = env['of.image']._prepare_mutation_values(**args)
        return env['of.image'].create(values)


class ImageUpdate(graphene.Mutation):
    _name = 'ImageUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()
        caption = graphene.String()
        sequence = graphene.Int()
        printable = graphene.Boolean()
        image_1920 = OdooImage()

    Output = Image

    def mutate(self, info, id, **args):
        env = info.context['env']
        values = env['of.image']._prepare_mutation_values(**args)
        image = env['of.image'].search([('id', '=', id)])
        image.write(values)
        return image


class ImageDelete(graphene.Mutation):
    _name = 'ImageDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = Image

    def mutate(self, info, id):
        env = info.context['env']
        return lazy_delete(env, 'of.image', id)


class ImageMutation(graphene.ObjectType):
    _name = 'ImageMutation'
    _type = 'mutation'

    image_create = ImageCreate.Field()
    image_update = ImageUpdate.Field()
    image_delete = ImageDelete.Field()
