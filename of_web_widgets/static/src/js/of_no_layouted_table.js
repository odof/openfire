/** @odoo-module **/

import { ListRenderer } from "@web/views/list/list_renderer";
import {patch} from "@web/core/utils/patch";

patch(ListRenderer.prototype, 'fixed_tree_width_one2many', {
    freezeColumnWidths() {
        if (!this.keepColumnWidths) {
            this.columnWidths = null;
        }

        const table = this.tableRef.el;
        const headers = [...table.querySelectorAll("thead th:not(.o_list_actions_header)")];

        if (!this.columnWidths || !this.columnWidths.length) {
            // no column widths to restore

            let allowedWidth;
            if (!this.props.list.context?.of_no_table_layouted) {  // OF no table layouted
                table.style.tableLayout = "fixed";
                allowedWidth = table.parentNode.getBoundingClientRect().width;
            }

            // Set table layout auto and remove inline style to make sure that css
            // rules apply (e.g. fixed width of record selector)
            table.style.tableLayout = "auto";
            headers.forEach((th) => {
                th.style.width = null;
                th.style.maxWidth = null;
            });

            this.setDefaultColumnWidths();

            // Squeeze the table by applying a max-width on largest columns to
            // ensure that it doesn't overflow

            if (!this.props.list.context?.of_no_table_layouted) {  // OF no table layouted
                this.columnWidths = this.computeColumnWidthsFromContent(allowedWidth);
            } else {
                this.columnWidths = this.computeColumnWidthsFromContent();
            }
            table.style.tableLayout = "fixed";
        }

        headers.forEach((th, index) => {
            if (!th.style.width) {
                th.style.width = `${Math.floor(this.columnWidths[index])}px`;
            }
        });
    }
})
