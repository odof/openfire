/** @odoo-module */
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

class OFTags extends Component {

    getTagProps(record) {
        if (this.props.fieldName){
            if (record.data[this.props.fieldName]){
                return {
                    id: record.id,
                    text: record.data[this.props.fieldName],
                }
            } else {
                return {
                    id: record.id,
                    text: record.data.display_name,
                };
            }
        } else {
            return {
                id: record.id,
                text: record.data.display_name,
            };
        }
    }

    get tags() {
        if (this.props.type == "char"){
            return [{ id: this.props.id, text: this.props.value }];
        } else {
            return this.props.value.records.map((record) => this.getTagProps(record));
        }
    }

}
OFTags.template = "of_web_widgets.OFTags";
OFTags.props = {
    ...standardFieldProps,
    fieldName: { type: String, optional: true}
};
OFTags.supportedTypes = ["char","many2many","one2many"];
OFTags.fieldsToFetch = {
    display_name: { type: "char" },
};
OFTags.extractProps = ({ attrs, field }) => {
    return {
        fieldName: attrs.options.field_name,
    };
};
registry.category("fields").add("of_tags", OFTags);
