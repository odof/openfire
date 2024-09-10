# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_base_graphql.graphql.image_type import Image


class SurveyQuestionAnswer(OdooObjectType):
    _name = "SurveyQuestionAnswer"
    _type = "types"

    id = graphene.Int(required=True)
    value = graphene.String()
    sequence = graphene.Int()
    is_correct = graphene.Boolean()
    is_default = graphene.Boolean()
    image = graphene.Field(Image)

    @staticmethod
    def resolve_image(root, info):
        return root.value_of_image_id or None


class SurveyQuestionAnswerInput(graphene.InputObjectType):
    _name = "SurveyQuestionAnswerInput"
    _type = "types"

    id = graphene.Int()
    value = graphene.String()
    sequence = graphene.Int()
    is_correct = graphene.Boolean()
    is_default = graphene.Boolean()


class SurveyQuestionAnswerFilterInput(SurveyQuestionAnswerInput):
    _name = "SurveyQuestionAnswerFilterInput"
