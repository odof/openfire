odoo.define('of_map_view.map_record', function (require) {
"use strict";

var Widget = require('web.Widget');

var MapRecord = Widget.extend({
	/**
	 *  Inits map_record
	 */
	init: function(parent, record, displayer, options) {
		//console.log('MapRecord.init arguments: ',arguments);
		this._super(parent);
		this.header_fields = options.header_fields;
		this.body_fields = options.body_fields;
		this.displayer = displayer;
		this.content = '';
		this.record = record;
		this.id = record.id;
		this.highlighted = false;

		this._compute_header_content();
		this._compute_body_content();

		this.start();
		//console.log('MapRecord inited: ',this);
	},
	/**
	 *	pre-renders map_record and binds events
	 */
	start: function() {
		var div_id = 'map_record_'+this.id;
		this.$el.addClass('o_map_record');
		this.$el.attr("id",div_id);

		this.$el.mouseover({on: true},this.do_toggle_highlighted);
		this.$el.mouseout({on: false},this.do_toggle_highlighted);
		this.$el.click(this.do_open_record);

		//console.log('MapRecord started: ',this);
		return this._super();
	},
	/**
	 *	Handles signal to highlight or downplay the map_record.
	 *
	 *	@param {Boolean} on true for highlighting, false for downplaying.
	 */
	do_toggle_highlighted: function(on) {
		//console.log('MapRecord.do_toggle_highlighted on: ',on);
		if (_.isBoolean(on)) {
			this.highlighted = !this.highlighted;
			this.displayer.do_highlight_record(this.id,on);
		}else{
			this.highlighted = !this.highlighted;
			this.displayer.do_highlight_record(this.id,this.highlighted);
		}
	},
    /**
     *	Handles signal to switch to the form view of a record. Triggers the view's custom event
     */
    do_open_record: function() {
    	this.do_toggle_highlighted(false);
    	this.displayer.view.trigger_up('map_record_open', {id: this.id});
    },
	/**
	 *	Renders the map_record's content
	 */
	render: function () {
		this.$el.append(this.get_content()).appendTo(this.displayer.container);

		return $.when();
	},
	/**
	 *	Returns map_record content as a string
	 */
	get_content: function() {
		return  this.header_content + this.body_content;
	},
	/**
	 *
	 */
	_compute_header_content: function() {
		this.header_content = '';
		var val;
		for (var i=0; i<this.header_fields.length; i++) {
			val = this.record[this.header_fields[i]];
			if (val) {
				this.header_content += val + '<br/>';
			}
		}
		this.header_content = '<strong>' + this.header_content + '</strong>';
		return $.when();
	},
	/**
	 *
	 */
	_compute_body_content: function() {
		this.body_content = '';
		var val;
		for (var i=0; i<this.body_fields.length; i++) {
			val = this.record[this.body_fields[i]];
			if (val) {
				this.body_content += val + '<br/>';
			}
		}
		return $.when();
	},

});

return MapRecord;
});