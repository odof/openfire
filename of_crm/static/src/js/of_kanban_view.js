odoo.define('of_crm.KanbanView', function (require) {
"use strict";

var KanbanView = require('web_kanban.KanbanView')

KanbanView.include({
	/**
	 *  changement de prospect à client et vice versa par drag n drop
	 */
	add_record_to_column: function (event) {
        var self = this;
        var column = event.target;
        var record = event.data.record;
        var data = {};
        data[this.group_by_field] = event.target.id;
        if (column.relation == "crm.stage") {
            if (column.title.toLowerCase() == 'gagné') {
                data['of_customer_state'] = 'customer';
            }else{
                data['of_customer_state'] = 'lead';
            }
        }
        this.dataset.write(record.id, data, {}).done(function () {
            if (!self.isDestroyed()) {
                self.reload_record(record);
                self.resequence_column(column);
            }
        }).fail(this.do_reload);
    },

});

return KanbanView;
});
