/** @odoo-module **/

import { registry } from "@web/core/registry";
const { Component, useEffect, useState, useRef, EventBus } = owl;
import { ListRenderer } from "@web/views/list/list_renderer";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";
import { usePopover } from "@web/core/popover/popover_hook";

import { PopupoverInfo, PopupoverDelete } from "./popupover";
import { Field } from "@web/views/fields/field";

export class OFInvoiceSectionLine extends Component {
    static template = "of_sale_layout_category.OFInvoiceSectionLine";
    static components = {
        Field,
        PopupoverInfo,
        PopupoverDelete
    }

    setup() {
        this.state = useState({
            nbColumns: this.props.columns.length,
        });
        this.section_column = this.props.columns.find((c) => c.name === "name");
        this.section_class = this.section_column && this.section_column.rawAttrs && this.section_column.rawAttrs.class;
        this.handle_column = this.props.columns.find((c) => c.name === "sequence");
        this.input_section_ref = useRef('inputSection');
        this.popover = usePopover();
        this.bus = new EventBus();

        useEffect(
            () => {this.state.nbColumns = this.props.columns.length;},
            () => [this.props.columns]
        )
    }

    showPopup(ev, popover, options) {
        this.closePopover = this.popover.add(
            ev.currentTarget,
            popover, { bus: this.bus, record: this.props.record, options: options }, {
                position: 'top',
            }
        );
        this.bus.addEventListener('close-popover', this.closePopover);
    }

    getSectionColumn() {
        return this.section_column;
    }

    getSectionClass() {
        return this.section_class;
    }

    getHandleColumn() {
        return this.handle_column;
    }

    async delete(evt) {
        await this.props.list.delete(this.props.record.id);
        await this.props.record.model.notify();
    }
}


export class OFInvoiceSectionListRenderer extends ListRenderer {
    static template = "of_sale_layout_category.OFInvoiceSectionListRenderer";
    static recordRowTemplate = "of_sale_layout_category.InvoiceListRenderer.RecordRow";
    static components = {
        Section: OFInvoiceSectionLine,
        ...ListRenderer.components,
    }

    setup() {
        super.setup();
        this.titleField = "name";
        this.titleFields = ["name", "of_section_name"];

        useEffect(
            () => this.focusToName(this.props.list.editedRecord),
            () => [this.props.list.editedRecord]
        )
    }

    focusToName(editRec) {
        if (editRec && editRec.isVirtual && this.isSectionOrNote(editRec)) {
            const col = this.state.columns.find((c) => c.name === this.titleField);
            this.focusCell(col, null);
        }
    }

    isSectionOrNote(record = null) {
        record = record || this.record;
        return ['line_section', 'line_note'].includes(record.data.display_type);
    }

    isSection(record = null) {
        record = record || this.record;
        return 'line_section' == record.data.display_type;
    }

    isNote(record = null) {
        record = record || this.record;
        return 'line_note' == record.data.display_type;
    }

    getRowClass(record) {
        const existingClasses = super.getRowClass(record);
        return `${existingClasses} o_is_${record.data.display_type} brighter-${record.data.of_level}`;

    }

    getColumns(record) {
        const columns = super.getColumns(record);
        if (this.isNote(record)) {
            return this.getNoteColumns(columns);
        }
        return columns;
    }

    getNoteColumns(columns) {
        const noteCols = columns.filter((col) => col.widget === "handle" || col.type === "field" && col.name === "name");
        return noteCols.map((col) => {
            if (col.name === "name") {
                return { ...col, colspan: columns.length - noteCols.length + 1 };
            } else {
                return { ...col };
            }
        });
    }
}

export class OFInvoiceSectionOne2Many extends X2ManyField {
    static additionalClasses = ['o_field_one2many'];
    static components = {
        ...X2ManyField.components,
        ListRenderer: OFInvoiceSectionListRenderer,
    };

}

registry.category("fields").add("of_invoice_section_one2many", OFInvoiceSectionOne2Many);
