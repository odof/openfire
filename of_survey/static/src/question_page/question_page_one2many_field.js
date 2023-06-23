/** @odoo-module */

import { OFQuestionPageListRenderer } from "./question_page_list_renderer";
import { registry } from "@web/core/registry";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";

const { useSubEnv } = owl;

class OFQuestionPageOneToManyField extends X2ManyField {
    setup() {
        super.setup();
        useSubEnv({
            openRecord: (record) => this.openRecord(record),
        });
    }
}
OFQuestionPageOneToManyField.components = {
    ...X2ManyField.components,
    ListRenderer: OFQuestionPageListRenderer,
};
OFQuestionPageOneToManyField.defaultProps = {
    ...X2ManyField.defaultProps,
    editable: "bottom",
};
OFQuestionPageOneToManyField.additionalClasses = ['o_field_one2many'];
registry.category("fields").add("of_question_page_one2many", OFQuestionPageOneToManyField);
