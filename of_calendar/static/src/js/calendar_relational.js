odoo.define('of_calendar.Many2ManyCalendarView', function (require) {
"use strict";

var common = require('web.form_common');
var core = require('web.core');
var data = require('web.data');
var CalendarView = require('web_calendar.CalendarView');
var form_relational = require('web.form_relational');

var FieldOne2Many = core.form_widget_registry.get('one2many');
var FieldMany2Many = core.form_widget_registry.get('many2many');

var _t = core._t;

var X2ManyCalendarView = CalendarView.extend({
    // Make modifications here about things that are both usable for calendar views of Many2many and One2many fields
    init: function () {
        var self = this;
        this._super.apply(this, arguments);
        this.parent_model = arguments[1].parent_view.dataset.model; // model of parent view
        this.parent_values = arguments[1].parent_view.datarecord; // field values of parent view
    }
});

var One2ManyCalendarView = X2ManyCalendarView.extend({
    // Make modifications here about things that are both usable for calendar views of One2many fields.
    // Overwrites X2ManyCalendarView
});

var Many2ManyCalendarView = X2ManyCalendarView.extend({
    // Make modifications here about things that are both usable for calendar views of Many2many and One2many fields.
    // Overwrites X2ManyCalendarView
});

core.view_registry
    .add('one2many_calendar', One2ManyCalendarView)
    .add('many2many_calendar', Many2ManyCalendarView);

core.one2many_view_registry
    .add('calendar', One2ManyCalendarView);

FieldOne2Many.include({
    init: function() {
        this._super.apply(this, arguments);
        this.x2many_views = _.extend(this.x2many_views, {
            calendar: One2ManyCalendarView,
        });
    },
});

FieldMany2Many.include({
    init: function() {
        this._super.apply(this, arguments);
        this.x2many_views = _.extend(this.x2many_views, {
            calendar: Many2ManyCalendarView,
        });
    },
});

core.form_widget_registry
    .add('many2many_calendar', FieldMany2Many)
    .add('one2many_calendar', FieldOne2Many)
});

