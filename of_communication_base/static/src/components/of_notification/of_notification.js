/** @odoo-module */

import { Component, useState } from '@odoo/owl';

const { markup } = owl;
export class Notification extends Component {
    /**
     * This class allows you to define a notification
     */
    static template = "of_communication_base.Notification";
    static props = {
        button_see_more_label: String,
        button_see_later_label: String,
        message: String,
        type: String,
        style: String,
        message_is_html: Boolean,
        message_id: String,
        is_preview: Boolean,
        recordNotificationMarkRecallAndRead: Function,
        title: String,
        date: Date,
        end_message: Date,
        summary: String,
        message_content: String,
        message_type: String,
    };

    setup() {
        /**
         * This function allows you to define that when configuring the preview of the notification,
         * it is visible
         */
        this.state = useState({
            visible: true,
            show: false,
            animationClass: 'slide-in',
            message_content: markup(this.props.message_content)
        });
    }

    async closePreviewNotification() {
        /**
         * This function allows you to no longer make the preview of the notification visible,
         */
        this.state.animationClass = 'slide-out';
        await new Promise(resolve => setTimeout(resolve, 500));
        this.state.visible = false;
    }

    async closeNotification() {
        /**
         * This function allows you to no longer make the notification visible,
         * And run a function which defines that the message has been read
         */
        this.state.animationClass = 'slide-out';
        await new Promise(resolve => setTimeout(resolve, 500));
        this.state.visible = false;
        this.props.recordNotificationMarkRecallAndRead(this.props.message_id, 'see');
    }

    async closeNotificationSeeMore() {
        /**
         * This function allows you to no longer make the notification visible,
         * And run a function which defines that the message has been read
         */
        this.state.animationClass = 'slide-out';
        await new Promise(resolve => setTimeout(resolve, 500));
        this.state.visible = false;
        this.props.recordNotificationMarkRecallAndRead(this.props.message_id, 'see');
        this.show();
    }

    async closeNotificationSeeLater(){
        /**
         * This function allows you to no longer make the notification visible,
         * And run a function which defines that the message has not been read
         */
        this.state.animationClass = 'slide-out';
        await new Promise(resolve => setTimeout(resolve, 500));
        this.state.visible = false;
        this.props.recordNotificationMarkRecallAndRead(this.props.message_id, 'not_see');
    }

    show() {
        /**
         * This function makes the message visible
         */
        this.state.show = true;
    }

    hide() {
        /**
         * This function allows you to no longer make the message visible
         */
        this.state.show = false;
    }
}
