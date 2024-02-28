odoo.define('of_service_parc_installe.planning_view', function (require) {
"use strict";

var PlanningView = require('of_planning_view.PlanningView')

PlanningView.PlanningRecord.include({
    init: function(row, view, record, options) {
        var res = this._super(row, view, record, options);
        this.parc_installe_product_name = record.parc_installe_product_name;
        return res;
        },
    });
})
