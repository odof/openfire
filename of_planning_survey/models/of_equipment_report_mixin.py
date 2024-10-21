# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class OFEquipmentReportMixin(models.AbstractModel):
    """Equipment Report Mixin to avoid code duplication for survey reports in equipment and intervention reports.

    Classes that inherit this mixin must define the '_answer_field_name' property.
    """

    _name = "of.equipment.report.mixin"
    _description = "Equipment Report Mixin"

    @property
    def _answer_field_name(self):
        """Override in child models to provide the name of the answers field."""
        raise NotImplementedError("Subclasses must define '_answer_field_name'")

    @property
    def answer_field(self):
        """Dynamically get the answer field."""
        return getattr(self, self._answer_field_name)

    def _report_of_get_pages_to_display(self):
        """Get sections to display."""
        self.ensure_one()
        pages = self.answer_field.filtered(lambda a: a.question_id.is_page)
        return pages.filtered(lambda page: self._report_of_display_page(page))

    def _report_of_display_page(self, page):
        """Determine if a section should be displayed.

        Args:
            page (of.survey.answers): Section to check.
        """
        page_answers = self.answer_field.filtered(lambda a: a.question_id in page.mapped("question_id.question_ids"))
        page_input_lines = page_answers.mapped("user_input.user_input_line_ids").filtered(
            lambda il: il.question_id in page.mapped("question_id.question_ids")
        )
        return not all(
            page_input_lines.mapped(
                lambda il: il.skipped or (il.answer_type == "multi_image" and len(il.value_image_ids) == 0)
            )
        )

    def _report_of_get_answers_to_display(self, page=None, report=False):
        """Get answers to display.

        Args:
            page (of.survey.answers): Section to filter on.
            report (bool): True if we are in the intervention report.
        """
        self.ensure_one()
        page_answers = self.answer_field

        if page:
            page_answers = page_answers.filtered(lambda a: a.question_id in page.mapped("question_id.question_ids"))

        return page_answers.filtered(lambda answer: self._report_of_display_answer(answer, report))

    def _report_of_display_answer(self, answer, report):
        """Determine if an answer should be displayed.

        Args:
            answer (of.survey.answers): Answer to check.
            report (bool): True if we are in the intervention report.
        """
        answer_input_line = answer.mapped("user_input.user_input_line_ids").filtered(
            lambda il: il.question_id in answer.question_id
        )

        return answer_input_line and not (
            (report and answer.question_id.constr_no_report_display)
            or all(answer_input_line.mapped("skipped"))
            or (answer.question_type == "multi_image" and len(answer_input_line.mapped("value_image_ids")) == 0)
        )
