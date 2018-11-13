odoo.define('of_web_widgets.of_form_relational', function (require) {
"use strict";

var form_relational = require('web.form_relational');
var core = require('web.core');
var data = require('web.data');
var common = require('web.form_common');
var Model = require('web.DataModel');
var Dialog = require('web.Dialog');

var FieldMany2One = form_relational.FieldMany2One;

var _t = core._t;

/**
 *  Field to somehow emulate the behavior of 1-1 connections
 *  Mostly works like a Many2one
 *  no value displayed: either Create or See
 *  no dropdown menu
 *  only a button that will open a pop up in "view", "create" and "edit" mode
 */
var FieldOne2One = FieldMany2One.extend({
    template: "FieldOne2One",

    init: function(field_manager, node) {
        this._super.apply(this, arguments);
        //console.log("FieldOne2One init this and arguments: ",this,arguments);

    },

    initialize_content: function() {  // override -> no call to parent function render_editable
        this.render_init();
    },

    render_init: function() {  // formerly render_editable()
        var self = this;

        if (!this.get("value")) {  // no value yet -> offer to create a record
            this.$el.click(function(ev) {
                ev.preventDefault();
                var context = self.build_context().eval();
                var model_obj = new Model(self.field.relation);
                model_obj.call('get_formview_id', [[self.get("value")], context]).then(function(view_id){
                    var pop = new common.FormViewDialog(self, {
                        res_model: self.field.relation,
                        res_id: self.get("value"),
                        context: self.build_context(),
                        title: _t("Create: ") + self.string,
                        view_id: view_id,
                        readonly: self.get('effective_readonly'),
                        disable_multiple_selection: true,  // disable button "save & new"
                    }).open();
                    pop.on('create_completed', self, function(new_id){
                        self.set("value", new_id);
                        var new_value = {}
                        new_value["" + this.get("value")] = this.get("value");
                        self.display_value = new_value;
                        self.display_value_backup = new_value;
                        self.render_value();
                        self.focus();
                        self.trigger('changed_value');
                    });
                    pop.on('record_saved', self, function(){  //
                        self.display_value = {};
                        self.display_value_backup = {};
                        self.render_value();
                        self.focus();
                        self.trigger('changed_value');
                    });
                });
            });
        }else{
            this.$el.click(function(ev) {
                ev.preventDefault();
                var context = self.build_context().eval();
                var model_obj = new Model(self.field.relation);
                model_obj.call('get_formview_id', [[self.get("value")], context]).then(function(view_id){
                    var pop = new common.FormViewDialog(self, {
                        res_model: self.field.relation,
                        res_id: self.get("value"),
                        context: self.build_context(),
                        title: _t("Open: ") + self.string,
                        view_id: view_id,
                        readonly: self.get('effective_readonly'),
                    }).open();
                    pop.on('record_saved', self, function(){
                        self.display_value = {};
                        self.display_value_backup = {};
                        self.render_value();
                        self.focus();
                        self.trigger('changed_value');
                        //console.log("record_saved B self: ",self);
                    });
                });
            });
        };

        this.setupFocus(this.$el);
    },

    display_string: function (str) {
        var noValue = (str === null);
        var text_empty = this.options.text_empty || _t("Create: ") + this.field.string;//_t(this.field.string);
        var text_nonempty = this.options.text_nonempty || _t("See: ") + _t(this.field.string);
        this.$el.html(noValue ? text_empty : text_nonempty || data.noDisplayContent);
    },
});

core.form_widget_registry
    .add('one2one', FieldOne2One);

return FieldOne2One;
});
