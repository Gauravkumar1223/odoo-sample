/** @odoo-module **/
import {registry} from "@web/core/registry";

function extractIdAndModel() {
    const url = new URL(window.location.href);
    const hash = url.hash;
    const params = new URLSearchParams(hash.substring(1)); // Remove the '#' before parsing
    const id = params.get('id');
    const model = params.get('model');
    return {id, model};
}

const WrrritPollingService = {
    dependencies: ['bus_service'],
    async start(_, {bus_service}) {
        // Extracting 'id' and 'model' from the URL
        let {id, model} = extractIdAndModel();
        model ="wrrrit.ai.voice_record"
        const channelName = `wrrrit-progress-${model}`;


        this.progressBarContainer = this.createProgressBar();
        //console.log(`Progress bar created: `, this.progressBarContainer);
        bus_service.addChannel(channelName);
        bus_service.addEventListener('notification', ({detail: notifications}) => {
            for (const {payload, type} of notifications) {
                if (type === channelName) {

                    this.wrrritProgressEventHandler(payload);
                }
            }
        });
        await bus_service.start();
       // console.log(`WrrritPollingService started for channel: ${channelName}`);


    },
    createProgressBar() {
        const progressBarContainer = document.createElement('div');
        progressBarContainer.style.position = 'fixed';
        progressBarContainer.style.top = '80px';
        progressBarContainer.style.left = '0';
        progressBarContainer.style.width = '100%';
        progressBarContainer.style.zIndex = '9999';

        const progressBar = document.createElement('div');
        progressBar.style.height = '10px'; // Thicker progress bar
        progressBar.style.width = '0%';
        progressBar.style.backgroundColor = 'darkred'; // Red color
        progressBar.style.transition = 'width 0.15s';

        progressBarContainer.appendChild(progressBar);
        document.body.appendChild(progressBarContainer);


        return progressBarContainer; // Return the container instead
    },
    wrrritProgressEventHandler(event) {

        const {id, model} = extractIdAndModel();
        const eventId = parseInt(event.record_id, 10); // Convert event.record_id to an integer
        const currentId = parseInt(id, 10); // Convert URL id to an integer



        if (eventId !== currentId || event.model_name !== model) {

            return;
        }


        this.updateProgressBar(event.progress);
    },
    updateProgressBar(progress) {

        const progressBar = this.progressBarContainer.firstChild;
        if (progressBar) {
            let currentWidth = parseFloat(progressBar.style.width) || 0;
            let newWidth = currentWidth + progress;
            newWidth = Math.min(newWidth, 100);
            progressBar.style.width = `${newWidth}%`;


            if (newWidth >= 99) {
                // If progress is 100%, reset the progress bar after a slight delay
                setTimeout(() => {
                    progressBar.style.width = '0%';
                }, 400); // Adjust the delay as needed
                const reloadButton = document.querySelector('button.reload_view');
                if (reloadButton) {
                    setTimeout(() => {
                        reloadButton.click();
                    }, 1000); // Adjust the delay as needed
                    reloadButton.click();
                }


                const showPanel = document.querySelector('.wrr_generated_clickable');
                if (showPanel) {
                    showPanel.click();
                }
                if (reloadButton) {
                    reloadButton.click();
                }

            }
        }
    }
};

registry.category("services").add("WrrritPollingService", WrrritPollingService);
