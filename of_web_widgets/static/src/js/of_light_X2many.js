/** @odoo-module */
import { registry } from "@web/core/registry";
import { ListRenderer } from "@web/views/list/list_renderer";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";


export class OFLightListRenderer extends ListRenderer {
    static template = "of_web_widgets.OFLightListRenderer";

    get getEmptyRowIds(){
        return [];
    }

}

export class OFLightX2many extends X2ManyField {
    static components = {
        ...X2ManyField.components,
        ListRenderer: OFLightListRenderer,
    };


}

registry.category("fields").add("of_light_x2many", OFLightX2many);
