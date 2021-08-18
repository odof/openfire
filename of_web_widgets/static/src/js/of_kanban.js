odoo.define('of_web_widgets.of_kanban', function (require) {
"use strict";

var core = require('web.core');
var formats = require('web.formats');
var Registry = require('web.Registry');
var Widget = require('web.Widget');
var QWeb = core.qweb;
var _t = core._t;
var utils = require('web.utils');
var data = require('web.data');
var Model = require('web.DataModel');
var datepicker = require('web.datepicker');

var web_k_widgets = require('web_kanban.widgets');
var AbstractField = web_k_widgets.AbstractField;
var web_k_registry = web_k_widgets.registry;

AbstractField.include({
    init: function() {
        this._super.apply(this, arguments);
        this.parent = arguments[0];
        this.update_read_only_mode();
    },
    /**
     *  NB : in the kanban record qweb template, one can now set a variable read_only_fields to force readonly
     */
    update_read_only_mode: function() {
        if (this.parent.qweb_context && this.parent.qweb_context.read_only_fields) {
            this.read_only_mode = true;
        }else{
            this.read_only_mode = this.parent.read_only_mode || false;
        }
    },
});

var OFKanbanSelection = AbstractField.extend({
    // inspired by web_kanban.widgets.KanbanSelection and web.form_widgets.FieldSelection
    template: "OFKanbanSelection",
    className: "of_kanban_selection",
    defaults: _.extend({},{
    }),

    init: function(parent, field, $node, options) {
        this._super.apply(this, arguments);
        this.name = $node.attr('name');
        this.parent = parent;
        this.records_orderer = new utils.DropMisordered(); // function query_values

        this.options = _.defaults(options||{},this.defaults);
        this.parent_context = this.parent.qweb_context;

        this.context = this.build_context();
        this.set("domain", this.build_domain().eval());
    },
    /**
     *  queries possible values and returns them in the form of an array of dictionaries {'id': id, 'name': name}. Called by renderElement
     */
    prepare_dropdown_selection: function() {
        var self = this;
        var _data = [];
        var def = $.Deferred();
        this.query_values().then(function () { // this.query_values() will set self.field.selection
            _.map(self.field.selection || [], function(res) {
                var value = {
                    'id': res[0],
                    'name': res[1],
                };
                _data.push(value);
            });
            def.resolve();
        });
        return $.when(def).then(function(){return _data;}); // asynchronicity
    },
    /**
     *  renders the element as text in readonly mode, as a dropdown menu in edit mode.
     */
    renderElement: function() {
        var self = this;
        var value;
        this.update_read_only_mode();

        if (this.read_only_mode) { // make it not selectable in read_only mode
            this.$el.text(formats.format_value(this.get('value'), this, ''));
        }else{
            this.prepare_dropdown_selection().then(function(res){
                self.values = res;
                var current_value;
                if (self.is_false()) {
                    current_value = {'id': -2, 'name': _t('Click to set value')};
                }else{
                    var self_value = self.get('value');
                    current_value = _.find(self.values, function(value) {
                        if (self_value instanceof Array) {
                            return value.id === self_value[0];
                        }else{ // kanban_view transforms arrays into integers to write into the database. see kanban_view.update_record
                            return value.id === self_value
                        }
                    }) || {'id': -1, 'name': _t('Unknown / Unset')};
                };
                var args = { // arguments passed to qweb template
                    current_value: current_value,
                    values: _.without(self.values, current_value) // don't display current value in dropdown menu
                }
                self.$el.html(QWeb.render(self.template, args));
                self.$('a').click(function (ev) {
                    ev.preventDefault();
                });
                self.$('a').click(self.set_kanban_selection.bind(self));
            });
        }
    },
    /**
     *  sets new value dict and sends signal to update record
     */
    set_kanban_selection: function(e) {
        e.preventDefault();
        var $li = $(e.target).closest( "li" );
        if ($li.length) {
            var dict = {};
            var value = [$li.data('id'), String($li.data('value'))];
            dict[this.name] = value;
            this.trigger_up('kanban_update_record', dict, this); // see kanban_record.update_record and kanban_view.update_record
        }
    },
    /**
     *  tweaked from FieldSelection.
     *  returns a promise targeting the possible values
     */
    query_values: function() {
        var self = this;
        var def;
        if (this.field.type === "many2one") { // supposed to be always the case, maybe force it with an error?
            var model = new Model(this.field.relation);
            def = model.call("name_search", ['', this.get("domain")], {"context": this.context});
        } else { // copied code
            var values = _.reject(this.field.selection, function (v) { return v[0] === false && v[1] === ''; });
            def = $.when(values);
        }
        var vals = [];
        var def2 = $.Deferred();
        var prom = def2.promise({target: vals});
        this.records_orderer.add(def).then(function(values) {
            if (! _.isEqual(values, self.field.selection)) {
                self.field.selection = values;
                vals = values;
                def2.resolve()
            }else{
                def2.resolve()
            }
        });
        return prom;
    },
    /**
     * Builds a new context usable for operations related to fields by merging
     * the fields'context with the action's context. from FieldSelection
     */
    build_context: function() {
        // only use the model's context if there is not context on the node
        var v_context = this.$node.context;
        if (! v_context) {
            v_context = (this.field || {}).context || {};
        }
        /* was in original function, commented for now because kanban AbstractField parent is not a field_manager
        if (v_context.__ref) {
            var fields_values = this.field_manager.build_eval_context();
            v_context = new data.CompoundContext(v_context).set_eval_context(fields_values);
        }*/
        return v_context;
    },
    /**
     *  builds domain according to attribute in XML view or in python file, XML view takes precedence
     */
    build_domain: function() {
        var f_domain = this.field.domain || [];
        var n_domain = this.$node[0].attributes.domain || null;
        // if there is a domain on the node, overrides the model's domain
        var final_domain = n_domain !== null ? n_domain : f_domain;
        var fields_values = this.build_eval_context();
        final_domain = new data.CompoundDomain(final_domain).set_eval_context(fields_values);
        var len = final_domain['__domains'].length;
        for (var i=0; i<len; i++){
            if (final_domain['__domains'][i]['value']) {
                final_domain['__domains'][i] = final_domain['__domains'][i]['value']
            }
        };

        return final_domain;
    },
    /**
     *
     */
    build_eval_context: function() {
        return new data.CompoundContext(this.build_context(),this._get_fields_values());
    },
    /**
     * Method useful to implement to ease validity testing. Must return true if the current
     * value is similar to false in OpenERP. see web.form_common.AbstractField
     */
    is_false: function() {
        return this.get('value') === '' || this.get('value') === false;
    },
    /**
     *  Returns record values as a dict of the form {field_name_1: field_value_1, field_name_2: field_value_2, ...}
     */
    _get_fields_values: function() {
        var values = {};
        _.each(this.parent.values, function(value_, key) {
            if (value_.value instanceof Array) { // take only the id (at index 0)
                values[key] = value_.value[0];
            }else{
                values[key] = value_.value;
            }
        });
        return values;
    },
});

var OFKanbanDate = AbstractField.extend({
    // inspired by web.form_widgets.FieldDate
    className: "of_kanban_date",
    tagName: 'span',
    defaults: _.extend({},{

    }),

    init: function(parent, field, $node, options) {
        this._super.apply(this, arguments);
        this.name = $node.attr('name');
        this.parent = parent;
        this.options = _.defaults(options||{},this.defaults);

        this.initialize_content();
    },
    /**
     *  creates a new instance of DateWidget. called by initialize_content to set this.datewidget
     */
    build_widget: function() {
        return new datepicker.DateWidget(this);
    },
    /**
     *  initialize self.datewidget
     */
    initialize_content: function() {
        if (this.datewidget) {
            this.datewidget.destroy();
            this.datewidget = undefined;
        }

        if (!this.read_only_mode) {
            this.datewidget = this.build_widget();
            this.datewidget.on('datetime_changed', this, function() {
                this.set_value(this.datewidget.get_value());
            });

            var self = this;
            this.datewidget.appendTo('<div>').done(function() {
                self.datewidget.$el.addClass(self.$el.attr('class'));
                self.replaceElement(self.datewidget.$el);
                self.datewidget.$input.addClass('of_kanban_form_input');
                self.setupFocus(self.datewidget.$input);
            });
        }
    },
    /**
     *  renders this.$el, as text in readonly mode
     */
    renderElement: function() {
        this.update_read_only_mode();
        if (this.read_only_mode) {
            this.$el.text(formats.format_value(this.get('value'), this, ''));
        } else {
            this.datewidget.set_value(this.get('value'));
        }
    },
    /**
     *  sets value and updates record
     */
    set_value: function(value) {
        this.set('value',value);
        var dict = {};
        dict[this.name] = value;
        this.trigger_up('kanban_update_record', dict, this); // see kanban_record.update_record and kanban_view.update_record
    },
    /**
     *  from a copy-paste
     */
    is_false: function() {
        return this.get('value') === '' || this._super();
    },
    /**
     *  from a copy-paste
     */
    setupFocus: function ($e) {
        var self = this;
        $e.on({
            focus: function () { self.trigger('focused'); },
            blur: function () { self.trigger('blurred'); }
        });
    },
    /**
     *  from a copy-paste
     */
    focus: function() {
        if (!this.read_only_mode) {
            return this.datewidget.$input.focus();
        }
        return false;
    },
});

var OFKanbanChar = AbstractField.extend({
    className: "of_kanban_char",
    events: {
        'change': 'handle_change',
    },
    defaults: _.extend({},{

    }),

    init: function(parent, field, $node, options) {
        this._super.apply(this, arguments);
        this.name = $node.attr('name');
        this.parent = parent;
        this.options = _.defaults(options||{},this.defaults);
    },
    /**
     *  inits this.$input and attaches it to this.$el
     */
    init_input: function() {
        var input_attrs = {
            type: 'text',
            class: 'of_kanban_char_input',
        };
        if (!this.is_false()) {
            input_attrs['value'] = this.get('value');
        }
        this.$input = this.make('input',input_attrs);
        this.$el.append(this.$input);
    },
    /**
     *  renders the element
     */
    renderElement: function() {
        var self = this;
        this.update_read_only_mode();
        if (this.read_only_mode) {
            this.$el.text(formats.format_value(this.get('value'), this, ''));
        }else{
            this.init_input();
            // don't open popup on click
            this.$el.click(function (ev) {
                ev.preventDefault();
            });
        }
    },
    /**
     *  handles change of value. called after clicking somewhere else than this.$el
     */
    handle_change: function () {
        if (this.$input.value !== this.get('value')) {
            this.set_value();
        }
    },
    /**
     *  sets value and updates record
     */
    set_value: function() {
        this.set('value',this.$input.value);
        var dict = {};
        var value = this.$input.value;
        dict[this.name] = value;
        this.trigger_up('kanban_update_record', dict, this); // see kanban_record.update_record and kanban_view.update_record
    },
    /**
     * Method useful to implement to ease validity testing. Must return true if the current
     * value is similar to false in OpenERP. see web.form_common.AbstractField
     */
    is_false: function() {
        return this.get('value') === '' || this.get('value') === false;
    },
});

var OFKanbanText = OFKanbanChar.extend({
    className: "of_kanban_text",
    defaults: _.extend({},{

    }),
    events: {
        'keyup': function (e) {
            if (e.which === $.ui.keyCode.ENTER) {
                e.stopPropagation();
            }
        },
        'keypress': function (e) {
            if (e.which === $.ui.keyCode.ENTER) {
                e.stopPropagation();
            }
        },
        'change': 'handle_change',
    },

    /**
     *  inits this.$input and attaches it to this.$el
     */
    init_input: function() {
        var input_attrs = {
            rows: '4',
            type: 'text',
            class: 'of_kanban_text_input',
        };
        if (!this.is_false()) {
            var input_content = this.get('value');
        }
        this.$input = this.make('textarea',input_attrs,input_content);
        this.$el.append(this.$input);
    },
    /**
     *  renders the element
     */
    renderElement: function() {
        var self = this;
        this.update_read_only_mode();
        if (this.read_only_mode) {
            var txt = this.get("value") || '';
            this.$el.toggleClass("of_kanban_text_input");
            this.$el.text(txt);
        }else{
            this.init_input();
            // don't open popup on click
            this.$el.click(function (ev) {
                ev.preventDefault();
            });
        }
    },
});

var OFKanbanBool = AbstractField.extend({
    className: "of_kanban_bool",
    custom_events: {
        'of_fa_button_clicked': 'on_button_clicked',
    },
    defaults: _.extend({},{
        default_up: true,
    }),

    init: function(parent, field, $node, options) {
        this._super.apply(this, arguments);
        this.name = $node.attr('name');
        this.parent = parent;
        this.options = _.defaults(options||{},this.defaults);

        this.$input = new OFFAToggleButton(this,{default_up: field.raw_value}); // initializes toggle button
        this.set('value',field.raw_value);
    },
    /**
     *  wait for this.$input to be rendered
     */
    start: function() {
        return $.when(this.$input.prependTo(this.$el),this._super());
    },
    /**
     *  toggles this.$input
     */
    do_toggle_button: function() {
        this.$input.do_toggle();
    },
    /**
     *  sets value and updates record
     */
    set_value: function(value) {
        this.set('value',value);
        var dict = {};
        dict[this.name] = value;
        this.trigger_up('kanban_update_record', dict, this); // see kanban_record.update_record and kanban_view.update_record
    },
    /**
     *  handles click on this.$input
     */
    on_button_clicked: function() {
        if (!this.read_only_mode) {
            this.do_toggle_button();
            this.set_value(!this.get('value'));
        }
    },
});

var OFFAButton = Widget.extend({
    // fontawesome button
    template: "OFFAButton",
    defaults: _.extend({},{
        fa_class: 'fa fa-square-o fa-lg',
    }),

    init: function(parent, options) {
        this._super.apply(this, arguments);
        this.parent = parent;
        this.options = _.defaults(options||{},this.defaults);
        this.read_only_mode = parent.read_only_mode || false;
    },
    /**
     *  disables button if readonly mode
     */
    start: function() {
        if (this.read_only_mode) {
            this.toggle_active();
        }
        return $.when(this._super());
    },
    /**
     *  renders this.$el and binds click event
     */
    renderElement: function() {
        var self = this;
        this.$el = $(QWeb.render(this.template, {widget: this}).trim());
        this.init_icon();
        this.$el.click(function (ev) {
            ev.preventDefault();
            self.parent.trigger_up('of_fa_button_clicked');
        });
    },
    /**
     *  makes the icon and attaches it to this.$el. Called by renderElement
     */
    init_icon: function() {
        var icon_attrs = {
            class: this.options.fa_class + " of_fa_button_i",
        };
        this.$icon = this.make('i',icon_attrs);
        this.$el.append(this.$icon);
    },
    /**
     *  toggles active/disabled status of button
     */
    toggle_active: function() {
        this.$el.toggleClass('active').toggleClass('disabled');
    },
});

var OFFAToggleButton = OFFAButton.extend({
    // fontawesome toggleable button
    defaults: _.extend({},{
        fa_class_down: 'fa fa-square-o fa-lg',
        fa_class_up: 'fa fa-check-square-o fa-lg',
        default_up: false,
    }),

    init: function(parent, options) {
        this._super.apply(this, arguments);
        this.is_up = this.options.default_up;
    },
    /**
     *  override to implement toggleability
     */
    init_icon: function() {
        var the_class;
        if (this.options.default_up) {
            the_class = this.options.fa_class_up + " of_fa_button_i";
        }else{
            the_class = this.options.fa_class_down + " of_fa_button_i";
        }
        var icon_attrs = {
            class: the_class,
        };
        this.$icon = this.make('i',icon_attrs);
        this.$el.append(this.$icon);
    },
    /**
     *  toggles up the button
     */
    do_toggle_up: function() {
        this.is_up = true;
        this.$icon.className = this.options.fa_class_up + " of_fa_button_i";
    },
    /**
     *  toggles down the button
     */
    do_toggle_down: function() {
        this.is_up = false;
        this.$icon.className = this.options.fa_class_down + " of_fa_button_i";
    },
    /**
     *  toggles the button
     */
    do_toggle: function() {
        if (this.is_up) {
            this.do_toggle_down();
        }else{
            this.do_toggle_up();
        }
    }
})

web_k_registry
    .add('of_kanban_selection', OFKanbanSelection)
    .add('of_kanban_date', OFKanbanDate)
    .add('of_kanban_char', OFKanbanChar)
    .add('of_kanban_text', OFKanbanText)
    .add('of_kanban_bool', OFKanbanBool)
    .add('of_fa_button', OFFAButton)
    .add('of_fa_toggle_button', OFFAToggleButton)
    ;

return {
    registry: web_k_registry,
    OFFAButton: OFFAButton,
    OFFAToggleButton: OFFAToggleButton,
};

});
