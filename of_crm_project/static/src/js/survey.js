odoo.define('of_crm_project.of_survey_form', function (require) {
'use strict';

    var OFSurveyFormWidget = require('of_survey.form');

    function sleep (time) {
      return new Promise((resolve) => setTimeout(resolve, time));
    }

    OFSurveyFormWidget.include({
        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                var button_submit = $("button[type='submit']");
                var show_start = $('.show_start').attr('data-show');
                if (show_start=='no'){
                    self._submitForm({});
                }
            });
        },

    });

    return OFSurveyFormWidget;

});
