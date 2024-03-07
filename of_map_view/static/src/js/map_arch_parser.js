/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { XMLParser } from "@web/core/utils/xml";

export class MapArchParser extends XMLParser{
    parse(arch) {
        let infoFromRootNode;
        const decorationFields = [];
        let popoverTemplate = null;

        this.visitXML(arch, (node) => {
            switch (node.tagName) {
                case "map": {
                    infoFromRootNode = getInfoFromRootNode(node);
                    break;
                }
                case "field": {
                    const fieldName = node.getAttribute("name");
                    decorationFields.push(fieldName);
                    break;
                }
                case "templates": {
                    popoverTemplate = node.querySelector("[t-name=map-popover]") || null;
                    if (popoverTemplate) {
                        popoverTemplate.removeAttribute("t-name");
                    }
                }
            }
        });

        return {
            ...infoFromRootNode,
            decorationFields,
            popoverTemplate,
        };
    }
}

function getInfoFromRootNode(rootNode) {
    const attrs = {};
    for (const { name, value } of rootNode.attributes) {
        attrs[name] = value;
    }

    return {
        width: attrs.width ? attrs.width : '150px',
        latitudeField: attrs.latitude,
        longitudeField: attrs.longitude,
        tooltipView: attrs.tooltip_view,
        formViewId: attrs.form_view_id ? parseInt(attrs.form_view_id, 10) : false,
    };
}
