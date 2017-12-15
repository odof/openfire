odoo.define('web.of_form_widgets', function (require) {
"use strict";
var core = require('web.core');
var data = require('web.data');
var _t = core._t;
var QWeb = core.qweb;
var form_widgets = require('web.form_widgets');
var FieldFloat = form_widgets.FieldFloat;

var OFFieldColorIndex = FieldFloat.extend({
	/*
	 * Ce widget sert à afficher une pastille de couleur à la place d'un entier
	 * Utile pour facilement visualiser la couleur d'une étiquette depuis la vue form de son modèle
	 */
	template: 'OFFieldColorIndex',
	events: {
		'mousedown .of_colorpicker span': 'update_color_o',
        'focusout .of_colorpicker': 'close_color_picker',
	},
	init: function() {
        this._super.apply(this, arguments);
        this.index = this.get('value');
    },
    initialize_content: function() {
    	this._super();
        this.$el.addClass('of_tag_color_'+this.get('value'));
    },
    renderElement: function(){
		var self = this;
		this._super.apply(this, arguments);
		if (!this.get('effective_readonly')){
			this.$el.click(function (ev) {
	            ev.preventDefault();
	            self.open_color_popup(ev);
	        });
			this.$el.focusout(function (ev) {
				ev.preventDefault();
				self.close_color_picker();
			});
		}
    },
    render_value: function() {
    	// ne rien faire <-surcharge fn parente
    },
    open_color_popup: function(ev){
        this.$color_picker = $(QWeb.render('OFFieldColorIndex.colorpicker', {
            'widget': this,
            'tag_id': $(ev.currentTarget).data('id'),
        }));
        var self = this;
        this.$el.append(this.$color_picker);
        this.$color_picker.dropdown('toggle');
        this.$color_picker.attr("tabindex", 1).focus();
    },
    close_color_picker: function(){
        this.$color_picker.remove();
    },
    update_color_o: function(ev) {
    	ev.preventDefault();
        var color = $(ev.currentTarget).closest('span').data('color');
        this.$el.removeClass('of_tag_color_'+this.get('value'));
        this.set_value(color);
        this.$el.addClass('of_tag_color_'+color);
    },
    set_value: function(value) {
		if (value != false) {
			this.set({'value': value});
		}else{
			this.set({'value': this.get('value')});
		}
    },
    store_dom_value: function () {
        if (this.$input && this.is_syntax_valid()) {
            this.internal_set_value(this.get('value'));
        }
    },
});

core.form_widget_registry
    .add('color_index', OFFieldColorIndex)

return OFFieldColorIndex;

});
