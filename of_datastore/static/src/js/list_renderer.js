/** @odoo-module **/
import { patch } from 'web.utils';
import { ListRenderer } from "@web/views/list/list_renderer";
patch(ListRenderer.prototype, 'list_renderer_of_datastore', {
    getRowClass(record) {
        let classNames = this._super(...arguments);
        if (record.resId < 0) {
            classNames += ' of_datastore_row';
        }
        return classNames;
    }
});
