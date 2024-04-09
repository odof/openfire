# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import models

from odoo.addons.of_graphql.graphql.odoo_graphql import OdooGraphql

from ..graphql.survey_mutation import SurveyMutation
from ..graphql.survey_query import SurveyQuery
from ..graphql.survey_question_answer_mutation import SurveyQuestionAnswerMutation
from ..graphql.survey_question_answer_query import SurveyQuestionAnswerQuery
from ..graphql.survey_question_answer_type import (
    SurveyQuestionAnswer,
    SurveyQuestionAnswerCreateInput,
    SurveyQuestionAnswerFilterInput,
    SurveyQuestionAnswerUpdateInput,
)
from ..graphql.survey_question_page_mutation import SurveyConditionalQuestionMutation, SurveyQuestionPageMutation
from ..graphql.survey_question_page_query import SurveyConditionalQuestionQuery, SurveyQuestionPageQuery
from ..graphql.survey_question_page_type import (
    SurveyConditionalQuestion,
    SurveyConditionalQuestionCreateInput,
    SurveyConditionalQuestionFilterInput,
    SurveyConditionalQuestionUpdateInput,
    SurveyQuestionPage,
    SurveyQuestionPageCreateInput,
    SurveyQuestionPageFilterInput,
    SurveyQuestionPageUpdateInput,
)
from ..graphql.survey_type import Survey, SurveyCreateInput, SurveyFilterInput, SurveyUpdateInput
from ..graphql.survey_user_input_line_mutation import SurveyUserInputLineMutation
from ..graphql.survey_user_input_line_query import SurveyUserInputLineQuery
from ..graphql.survey_user_input_line_type import (
    SurveyUserInputLine,
    SurveyUserInputLineCreateInput,
    SurveyUserInputLineFilterInput,
    SurveyUserInputLineUpdateInput,
)
from ..graphql.survey_user_input_mutation import SurveyUserInputMutation
from ..graphql.survey_user_input_query import SurveyUserInputQuery
from ..graphql.survey_user_input_type import (
    SurveyUserInput,
    SurveyUserInputCreateInput,
    SurveyUserInputFilterInput,
    SurveyUserInputUpdateInput,
)


class OFGraphql(models.AbstractModel):
    _inherit = 'of.graphql'

    def _of_survey_graphql_register(self, dbname):
        # ici on charge le graphql de ce module
        OdooGraphql.add(
            dbname,
            [
                SurveyConditionalQuestionMutation,
                SurveyConditionalQuestionQuery,
                SurveyConditionalQuestion,
                SurveyConditionalQuestionFilterInput,
                SurveyConditionalQuestionCreateInput,
                SurveyConditionalQuestionUpdateInput,
                SurveyMutation,
                SurveyQuery,
                Survey,
                SurveyFilterInput,
                SurveyCreateInput,
                SurveyUpdateInput,
                SurveyQuestionAnswerMutation,
                SurveyQuestionAnswerQuery,
                SurveyQuestionAnswer,
                SurveyQuestionAnswerFilterInput,
                SurveyQuestionAnswerCreateInput,
                SurveyQuestionAnswerUpdateInput,
                SurveyQuestionPageMutation,
                SurveyQuestionPageQuery,
                SurveyQuestionPage,
                SurveyQuestionPageFilterInput,
                SurveyQuestionPageCreateInput,
                SurveyQuestionPageUpdateInput,
                SurveyUserInputLineMutation,
                SurveyUserInputLineQuery,
                SurveyUserInputLine,
                SurveyUserInputLineCreateInput,
                SurveyUserInputLineFilterInput,
                SurveyUserInputLineUpdateInput,
                SurveyUserInputMutation,
                SurveyUserInputQuery,
                SurveyUserInput,
                SurveyUserInputFilterInput,
                SurveyUserInputCreateInput,
                SurveyUserInputUpdateInput,
            ],
        )
