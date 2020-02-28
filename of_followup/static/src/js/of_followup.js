odoo.define('of_followup.followup_kanban', function(require) {
    "use strict";

    var core = require('web.core');
    var KanbanView = require('web_kanban.KanbanView');

    var OFKanbanView = KanbanView.extend({
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

    core.view_registry.add('kanban', OFKanbanView);

    return OFKanbanView;
});