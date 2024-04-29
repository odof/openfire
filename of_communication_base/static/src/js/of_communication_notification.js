/** @odoo-module **/

import {registerPatch} from "@mail/model/model_core";

import { Notification } from "../components/of_notification/of_notification";

import { mount } from '@odoo/owl';
import { templates } from "@web/core/assets";

registerPatch({
    name: "MessagingNotificationHandler",
    recordMethods: {
        /**
         * @override
         */
        async _handleNotification(message) {
            /**
             * This function retrieves a message and returns it to the function that processes this type of message
             */
            const notificationProps =  {
                ...message.payload,
                recordNotificationMarkRecallAndRead: async (messageId, actionType) => {
                    await this.messaging.rpc({
                        model: 'of.communication.notification.log',
                        method: 'mark_message',
                        args: [messageId, actionType]
                    }, { shadow: true });
                },
            }

            if (message.type === "of_banner_notification") {
                return this._handleNotificationOF(notificationProps, 'banner');
            }
            if (message.type === "of_popup_notification") {
                return this._handleNotificationOF(notificationProps, 'pop-up');
            }
            if (message.type === "of_notification_removal") {
                return this._handleDeleteNotificationOF(notificationProps);
            }
            return this._super(message);
        },

        async _handleNotificationOF(props, type) {
            /**
             * This function retrieves a message,
             * Then create a root div if one does not exist and position it after the nav bar,
             * And then mount the components,
             * And finally puts a limit on the 3 most recent div
             */
            const container = document.querySelector("nav.o_main_navbar");
            if (!container) return;

            let rootId, className;
            if (type === 'banner') {
                rootId = 'banner-notification-root';
                className = 'banner-notification-root';
            } else if (type === 'pop-up') {
                rootId = 'pop-up-notification-root';
                className = 'pop-up-notification-root';
            }

            let ComponentRoot = document.getElementById(rootId);
            if (!ComponentRoot) {
                ComponentRoot = document.createElement('div');
                ComponentRoot.id = rootId;
                ComponentRoot.setAttribute('class', className);
                container.insertAdjacentElement('afterend', ComponentRoot);
            }
            const rootElement = document.getElementById(rootId);

            const existingMessageId = document.querySelectorAll(`div[message-id="${props.message_id}"]`);

            if (existingMessageId.length != 1) {
                await mount(Notification, rootElement, {
                    props: props,
                    templates,
                });
            }

            const existingNotifications = Array.from(rootElement.querySelectorAll(`.${className.split('-')[0]}`));

            existingNotifications.sort((a, b) => {
                const messageIdA = parseInt(a.getAttribute('message-id'));
                const messageIdB = parseInt(b.getAttribute('message-id'));
                return messageIdB - messageIdA;
            });

            while (existingNotifications.length > 3) {
                rootElement.removeChild(existingNotifications.pop());
            }
        },


        async _handleDeleteNotificationOF(props) {
            /**
             * This function retrieves information from a message,
             * It finds the notification by its message ID and removes it from the DOM.
             */
            let notification_type;

            if (props.notification_type == 'pop-up') {
                notification_type = 'pop-up-notification-root'
            } else if (props.notification_type == 'banner') {
                notification_type = 'banner-notification-root'
            }
            const rootElementId = notification_type
            const rootElement = document.getElementById(rootElementId);

            if (!rootElement) return;

            const existingNotifications = Array.from(rootElement.querySelectorAll(`div[message-id="${props.message_id}"]`));
            console.log('Existing Notifications:', existingNotifications);

            existingNotifications.forEach(notification => {
                rootElement.removeChild(notification);
            });
        },
    }
})
