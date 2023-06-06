odoo.define('of_crm.KanbanView', function (require) {
"use strict";

var KanbanView = require('web_kanban.KanbanView')
var Model = require('web.DataModel');

function _get_column_proba(records,name) {
    name = name.toLowerCase();
    var proba = 0;
    for (var i in records) {
        if (records[i]["name"].toLowerCase() == name) {
            proba = records[i]["probability"];
            break;
        }
    }
    return proba;
}

KanbanView.include({
    /**
     *  Changement de prospect à client et vice-versa par drag and drop
     */
    add_record_to_column: function (event) {
        var self = this;
        var column = event.target;
        var record = event.data.record;
        var data = {};
        data[this.group_by_field] = event.target.id;
        if (column.relation == "crm.stage") {
            var model = new Model("crm.stage");
            model.query(["name","probability"])
            .all()
            .then(function (res) {
                var proba = _get_column_proba(res,column.title);
                if (proba == 100) {
                    data['of_customer_state'] = 'customer';
                }
                self.dataset.write(record.id, data, {}).done(function () {
                    if (!self.isDestroyed()) {
                        self.reload_record(record);
                        self.resequence_column(column);
                    }
                }).fail(self.do_reload);
            })
        }else{
            this.dataset.write(record.id, data, {}).done(function () {
                if (!self.isDestroyed()) {
                    self.reload_record(record);
                    self.resequence_column(column);
                }
            }).fail(this.do_reload);
        }
    },

});

return KanbanView;
});
