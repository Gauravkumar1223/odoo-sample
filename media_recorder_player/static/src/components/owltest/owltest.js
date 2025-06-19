/** @odoo-module **/
import {Component, onMounted, onWillStart, onWillUnmount, useState} from '@odoo/owl';
import {registry} from '@web/core/registry';
import {standardFieldProps} from '@web/views/fields/standard_field_props';
import {loadJS} from "@web/core/assets";
class OwlLifecycleComponent extends Component {
    setup() {
        this.state = useState({
            log: 'Component setup.\n',
            isRecording: false,
            recordings: []
        });


        onWillStart(async () => {
            this.appendLog('Component will start.');
            await loadJS('https://unpkg.com/wavesurfer.js@7.6.4/dist/wavesurfer.min.js');
            await loadJS('https://unpkg.com/wavesurfer.js@7.6.4/dist/plugins/record.min.js');


            await loadJS('https://cdn.jsdelivr.net/npm/howler@2.2.1/dist/howler.min.js');
            await loadJS("https://unpkg.com/peaks.js/dist/peaks.js");

        });


        onMounted(() => {
            this.audioPlayer = document.getElementById('audio-player');
            this.appendLog('Component mounted.');
            this.appendLog('Audio player assigned.');
            const WaveSurfer = window.WaveSurfer || WaveSurfer; // depending on how the library exposes itself

            this.wavesurfer = WaveSurfer.create({
                container: '#waveform-owl',
                waveColor: 'violet',
                progressColor: 'purple'
            });
            this.appendLog("WaveSurfer Options:", JSON.stringify(this.wavesurfer.options, null, 2));
            console.log("WaveSurfer Options:", this.wavesurfer.options);
            if (this.wavesurfer) {
                const properties = Object.getOwnPropertyNames(Object.getPrototypeOf(this.wavesurfer));
                const methods = properties.filter(prop => typeof this.wavesurfer[prop] === 'function');
                this.appendLog('WaveSurfer methods:', JSON.stringify(methods, null, 2));
            }
        });

        onWillUnmount(() => {
            this.cleanupMedia();
            this.appendLog('Component will unmount.');
        });
    }

    appendLog(...messages) {
        const now = new Date();
        const timestamp = now.toLocaleTimeString(); // Format: "hh:mm:ss AM/PM"
        const formattedMessage = messages.join(' ');
        this.state.log += `${timestamp}: ${formattedMessage}\n`;
    }

    async initializeRecorder() {
        try {
            const constraints = {
                audio: {
                    echoCancellation: true,
                    sampleRate: 16000,

                    output: false,
                }
            };
            this.mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.analyser = this.audioContext.createAnalyser();
            this.source = this.audioContext.createMediaStreamSource(this.mediaStream);
            this.source.connect(this.analyser);
            this.analyser.connect(this.audioContext.destination);
            this.recorder = new MediaRecorder(this.mediaStream);
            this.appendLog('Recorder initialized.');
        } catch (error) {
            console.error('Error initializing recorder:', error);
            this.appendLog(`Error initializing recorder: ${error.message}`);
        }
    }

    assignCanvas() {
        this.canvas = document.getElementById('waveform-owl');
        if (this.canvas) {
            this.canvasContext = this.canvas.getContext('2d');
            //this.analyser.fftSize = 2048;
            this.bufferLength = this.analyser.frequencyBinCount;
            this.dataArray = new Uint8Array(this.bufferLength);
        } else {
            console.error('Canvas element was not found.');
        }
    }

    drawWaveform() {
        if (!this.isDestroying) {
            requestAnimationFrame(() => this.drawWaveform());
            this.analyser.getByteTimeDomainData(this.dataArray);

            this.canvasContext.fillStyle = 'rgb(200, 200, 200)';
            this.canvasContext.fillRect(0, 0, this.canvas.width, this.canvas.height);

            this.canvasContext.lineWidth = 2;
            this.canvasContext.strokeStyle = 'rgb(0, 0, 0)';
            this.canvasContext.beginPath();

            let sliceWidth = this.canvas.width * 1.0 / this.bufferLength;
            let x = 0;

            for (let i = 0; i < this.bufferLength; i++) {
                let v = this.dataArray[i] / 128.0;
                let y = v * this.canvas.height / 2;

                if (i === 0) {
                    this.canvasContext.moveTo(x, y);
                } else {
                    this.canvasContext.lineTo(x, y);
                }
                x += sliceWidth;
            }

            this.canvasContext.lineTo(this.canvas.width, this.canvas.height / 2);
            this.canvasContext.stroke();
        }
    }


    async startRecording() {
        this.appendLog('Recording started.');
        await this.initializeRecorder();
        this.assignCanvas();
        this.state.isRecording = true;
        this.recorder.start();
        this.recorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                let url = URL.createObjectURL(event.data);
                this.audioPlayer.src = url;
                this.state.recordings.push(url);

                this.appendLog('Recording saved.');
                this.drawWaveform();
            }
        };

    }

    async stopRecording() {
        this.appendLog('Recording stopped.');
        this.state.isRecording = false;
        this.recorder.stop();
        this.isDestroying = true;
        this.cleanupMedia();
    }


    cleanupMedia() {
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach((track) => track.stop());
        }
        if (this.audioContext) {
            this.audioContext.close();
        }
        if (this.recorder) {
            this.recorder.stream.getTracks().forEach((track) => track.stop());

        }

    }
}

OwlLifecycleComponent.template = 'media_player_recorder.OwlLifecycleComponent';
OwlLifecycleComponent.props = {...standardFieldProps};

registry.category('fields').add('owl_lifecycle', OwlLifecycleComponent);

export default OwlLifecycleComponent;