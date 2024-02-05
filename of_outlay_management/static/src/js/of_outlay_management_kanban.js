odoo.define('of_outlay_management.of_outlay_mngt_kanban', function(require) {
    "use strict";

    var KanbanView = require('web_kanban.KanbanView');

    KanbanView.include({
        render_grouped: function(fragment) {
            this._super.apply(this, arguments);
            // Remove drag and drop for columns
            var attrs = this.fields_view.arch.attrs;
            if (!this.is_action_enabled('drag_group')) {
                this.$el.sortable('option', 'disabled', true);
                for (var index in this.widgets) {
                    this.widgets[index].$header.css('cursor', 'auto');
                }
            }
        }
    });
});
