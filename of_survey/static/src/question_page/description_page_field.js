/** @odoo-module */

import { CharField } from "@web/views/fields/char/char_field";
import { registry } from "@web/core/registry";

const { useEffect, useRef } = owl;

class OFDescriptionPageField extends CharField {
    setup() {
        super.setup();
        const inputRef = useRef("input");
        useEffect(
            (input) => {
                if (input) {
                    input.classList.add("col");
                }
            },
            () => [inputRef.el]
        );
    }
    onExternalBtnClick() {
        this.env.openRecord(this.props.record);
    }
}
OFDescriptionPageField.template = "of_survey.OFDescriptionPageField";

registry.category("fields").add("of_survey_description_page", OFDescriptionPageField);
