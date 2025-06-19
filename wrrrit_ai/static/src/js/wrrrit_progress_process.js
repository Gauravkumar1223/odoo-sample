//** @odoo-module **/
import {Component, useState} from '@odoo/owl';
import {registry} from '@web/core/registry';
import {useService} from '@web/core/utils/hooks';


export class ProcessProgressWidget extends Component {
    setup() {
        console.log('setup starting process progress widget');
        this.state = useState({
            progress: 0,
        });

        this.bus = useService('bus');
        this.bus.on('notification', this, this._onNotification);
        this.bus.startPolling();
        this.bus.addChannel('long_process');
    }

    _onNotification(notifications) {
        for (const [channel, message] of notifications) {
            if (channel === 'long_process') {
                this.state.progress = message.progress;
            }
        }
    }

    willUnmount() {
        this.bus.deleteChannel('long_process');
        this.bus.off('notification', this);
    }
}

ProcessProgressWidget.template = "wrrrit_ai.ProcessProgressWidget";

registry.category("fields").add("process_progress", ProcessProgressWidget);
