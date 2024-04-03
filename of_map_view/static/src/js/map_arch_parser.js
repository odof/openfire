/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import {
    addFieldDependencies,
    archParseBoolean,
    getActiveActions,
    getDecoration,
    processButton,
    stringToOrderBy,
} from "@web/views/utils";
import { Field } from "@web/views/fields/field";
import { XMLParser } from "@web/core/utils/xml";
import { Widget } from "@web/views/widgets/widget";

export class MapArchParser extends XMLParser {
    isColumnVisible(columnInvisibleModifier) {
        return columnInvisibleModifier !== true;
    }

    parseFieldNode(node, models, modelName) {
        return Field.parseFieldNode(node, models, modelName, "map");
    }

    parseWidgetNode(node, models, modelName) {
        return Widget.parseWidgetNode(node);
    }

    processButton(node) {
        return processButton(node);
    }

    parse(arch, models, modelName) {
        const decorationFields = [];
        let popoverTemplate = null;
        const xmlDoc = this.parseXML(arch);
        const fieldNodes = {};
        const columns = [];
        let buttonId = 0;
        let headerButtons = [];
        const creates = [];
        let buttonGroup;
        let handleField = null;
        let defaultOrder = stringToOrderBy(
            xmlDoc.getAttribute("default_order") || null
        );
        const mapAttr = {};
        let nextId = 0;
        const activeFields = {};
        this.visitXML(arch, (node) => {
            if (node.tagName !== "button") {
                buttonGroup = undefined;
            }
            if (node.tagName === "button") {
                const modifiers = JSON.parse(node.getAttribute("modifiers") || "{}");
                if (this.isColumnVisible(modifiers.column_invisible)) {
                    const button = {
                        ...this.processButton(node),
                        defaultRank: "btn-link",
                        type: "button",
                        id: buttonId++,
                    };
                    if (buttonGroup) {
                        buttonGroup.buttons.push(button);
                    } else {
                        buttonGroup = {
                            id: `column_${nextId++}`,
                            type: "button_group",
                            buttons: [button],
                            hasLabel: false,
                        };
                        columns.push(buttonGroup);
                    }
                }
            } else if (node.tagName === "field") {
                // In map, we display one2many fields as tags by default
                const widget = node.getAttribute("widget");
                if (!widget && ["one2many", "many2many"].includes(models[modelName][node.getAttribute("name")].type)) {
                    node.setAttribute("widget", "many2many_tags");
                }
                const fieldName = node.getAttribute("name");
                decorationFields.push(fieldName);
                const fieldInfo = this.parseFieldNode(node, models, modelName);
                fieldNodes[fieldInfo.name] = fieldInfo;
                node.setAttribute("field_id", fieldInfo.name);
                if (fieldInfo.widget === "handle") {
                    handleField = fieldInfo.name;
                }
                addFieldDependencies(
                    activeFields,
                    models[modelName],
                    fieldInfo.FieldComponent.fieldDependencies
                );
                if (this.isColumnVisible(fieldInfo.modifiers.column_invisible)) {
                    const { label } = fieldInfo.FieldComponent;
                    columns.push({
                        ...fieldInfo,
                        id: `column_${nextId++}`,
                        className: node.getAttribute("class"), // for oe_edit_only and oe_read_only
                        optional: node.getAttribute("optional") || false,
                        type: "field",
                        hasLabel: !(
                            fieldInfo.noLabel || fieldInfo.FieldComponent.noLabel
                        ),
                        label:
                            (fieldInfo.widget && label && label.toString()) ||
                            fieldInfo.string,
                    });
                }
                return false;
            } else if (node.tagName === "templates") {
                popoverTemplate = node.querySelector("[t-name=map-popover]") || null;
                if (popoverTemplate) {
                    popoverTemplate.removeAttribute("t-name");
                }
            } else if (node.tagName === "map") {
                const activeActions = {
                    ...getActiveActions(xmlDoc),
                    exportXlsx: archParseBoolean(
                        xmlDoc.getAttribute("export_xlsx"),
                        true
                    ),
                };
                mapAttr.activeActions = activeActions;

                mapAttr.className = xmlDoc.getAttribute("class") || null;
                mapAttr.editable = activeActions.edit
                    ? xmlDoc.getAttribute("editable")
                    : false;
                mapAttr.multiEdit = activeActions.edit
                    ? archParseBoolean(node.getAttribute("multi_edit") || "")
                    : false;

                const limitAttr = node.getAttribute("limit");
                mapAttr.limit = limitAttr && parseInt(limitAttr, 10);

                const countLimitAttr = node.getAttribute("count_limit");
                mapAttr.countLimit = countLimitAttr && parseInt(countLimitAttr, 10);

                mapAttr.groupsLimit = 0;

                mapAttr.noOpen = archParseBoolean(node.getAttribute("no_open") || "");
                mapAttr.rawExpand = xmlDoc.getAttribute("expand");
                mapAttr.decorations = getDecoration(xmlDoc);

                // custom open action when clicking on record row
                const action = xmlDoc.getAttribute("action");
                const type = xmlDoc.getAttribute("type");
                mapAttr.openAction = action && type ? { action, type } : null;

                const widthAttr = node.getAttribute("width");
                mapAttr.width = (widthAttr && parseInt(widthAttr, 10)) || 150;
                mapAttr.latitudeField = node.getAttribute("latitude");
                mapAttr.longitudeField = node.getAttribute("longitude");
                mapAttr.colorField = node.getAttribute("color");
                mapAttr.tooltipView = node.getAttribute("tooltip_view");
            }
        });

        if (!defaultOrder.length && handleField) {
            defaultOrder = stringToOrderBy(handleField);
        }

        for (const [key, field] of Object.entries(fieldNodes)) {
            activeFields[key] = field; // TODO process
        }

        return {
            decorationFields,
            popoverTemplate,
            creates,
            handleField,
            headerButtons,
            fieldNodes,
            activeFields,
            columns,
            defaultOrder,
            __rawArch: arch,
            ...mapAttr,
        };
    }
}
