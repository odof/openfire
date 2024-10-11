# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one, x2many
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain

convert_type_dict = {
    "simple_choice": "suggestion",
    "multiple_choice": "suggestion",
    "text_box": "text_box",
    "char_box": "char_box",
    "date": "date",
    "multi_image": "multi_image",
    "form": "form",
    "numerical_box": "numerical_box",
}


class OFSurveyUserInputLine(models.Model):
    _inherit = "of.survey.user_input.line"

    @api.model
    def _handle_multiple_or_simple_choice_comment(self, question, args):
        """Handles the logic for simple and multiple choice questions when a comment is provided."""
        mutation2 = False

        if question.question_type == "simple_choice":
            args["answer_type"] = "char_box"
            args["value_char_box"] = args.get("comment")
        elif question.question_type == "multiple_choice":
            # Check if this line already exists in the database
            if id := args.get("id"):
                # It may be an update of an existing line
                if user_input := self.env["of.survey.user_input"].search([("user_input_line_ids", "in", [id])]):
                    lines = self.env["of.survey.user_input.line"].search(
                        [
                            ("user_input_id", "=", user_input.id),
                            ("question_id", "=", question.id),
                            ("skipped", "=", True),
                        ]
                    )
                    if len(lines) == 0:
                        # If there is no line with `skipped=True`, we need to create a new line with `skipped=True`
                        # for all the other answers
                        self.env["of.survey.user_input.line"].create(
                            {
                                "skipped": True,
                                "question_id": question.id,
                                "answer_type": False,
                                "suggested_answer_id": False,
                                "user_input_id": user_input.id,
                            }
                        )
            else:
                # As we only have a comment in the args, we need to create a new line with `skipped=True` for all
                # the other answers
                mutation2 = {
                    "skipped": True,
                    "question_id": question.id,
                    "answer_type": False,
                    "suggested_answer_id": False,
                }

            args["answer_type"] = "char_box"
            args["value_char_box"] = args.get("comment")
            args["skipped"] = False

        return mutation2

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}
        mutation2 = False

        if question_id := args.get("question"):
            question = self.env["of.survey.question"].browse(question_id)
            if question.question_type in ["simple_choice", "multiple_choice"] and args.get("comment"):
                # Handle the logic for simple and multiple choice questions when a comment is provided
                # This will return a second mutation if needed
                mutation2 = self._handle_multiple_or_simple_choice_comment(question, args)

        if "skipped" in args:
            mutation["skipped"] = args["skipped"]

        if "answer_type" in args:
            mutation["answer_type"] = args["answer_type"]
        elif question_id := args.get("question"):
            if question_id:
                # on va chercher le type sur la question
                odoo_question = self.env["of.survey.question"].browse(question_id)
                if odoo_question.question_type in convert_type_dict:
                    mutation["answer_type"] = convert_type_dict[odoo_question.question_type]

        if value_char_box := args.get("value_char_box"):
            mutation["value_char_box"] = value_char_box

        if value_date := args.get("value_date"):
            mutation["value_date"] = value_date

        if value_text_box := args.get("value_text_box"):
            mutation["value_text_box"] = value_text_box

        if value_numerical_box := args.get("value_numerical_box"):
            mutation["value_numerical_box"] = value_numerical_box

        if suggested_answer := args.get("suggested_answer"):
            mutation["suggested_answer_id"] = many2one(
                self=self, model="of.survey.question.answer", input=suggested_answer
            )

        if question_id := args.get("question"):
            mutation["question_id"] = question_id

        if "images" in args:
            mutation["value_image_ids"] = x2many(self=self, model="of.image", input=args.get("images"))

        return [mutation, mutation2] if mutation2 else mutation

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = []

        if domain:
            odoo_domain = graphqlOdooDomain(self=self, model="of.survey.user_input.line", domain=domain)

        if select:
            if select.id:
                odoo_domain += [("id", "=", select.id)]
            if select.name:
                odoo_domain += [("name", "like", select.name)]

        return odoo_domain
