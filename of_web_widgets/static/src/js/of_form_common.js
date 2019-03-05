odoo.define('of_web_widgets.of_form_common', function (require) {
"use strict";

var form_common = require('web.form_common');
var utils = require('web.utils');

form_common.CompletionFieldMixin.init = function(){
	this.limit = 7;
	this.orderer = new utils.DropMisordered();
	this.can_create = this.node.attrs.can_write == "false" ? false : true;
	this.can_write = this.node.attrs.can_write == "false" ? false : true;
	this.options.no_quick_create = true;
	//console.log(" test : ", this.options);
};

});
