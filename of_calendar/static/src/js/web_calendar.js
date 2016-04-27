
// Desactivation du drag-and-drop dans la vue calendar
odoo.define('of_calendar.of_calendar', function (require) {
"use strict";

var CalendarView = require('web_calendar.CalendarView');

CalendarView.include({

    get_fc_init_options: function () {
        var fc = this._super();
        fc.editable = false;
        return fc;
    },

});

});
