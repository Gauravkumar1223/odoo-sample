/** @odoo-module */

import {Component, onMounted, onWillStart, onWillUnmount, useEffect, useRef, useState} from "@odoo/owl";
import {standardFieldProps} from "@web/views/fields/standard_field_props";
import {registry} from "@web/core/registry";
import {loadJS} from "@web/core/assets";
import {useService} from '@web/core/utils/hooks';

const darkThemeColors = {
    waveColor: "linear-gradient(135deg, rgba(0,120,120,1) 0%, rgba(0,150,150,1) 100%)",
    progressColor: "#ff8a65",
    cursorColor: "#ffd740",
    gridColor: "rgba(150, 150, 150, 0.5)",
};

class VoiceRecorderComponent extends Component {
    setup() {
        this.state = useState({
            isRecording: false,
            isPaused: false,
            isPlaying: false,
            zoomLevel: 20,
            recordings: [],
            recordingStatus: "stopped",
            playbackInstance: null,
            currentTime: "00:00",
            duration: 0,
            currentSrc: null,
            hasRecording: false,
            audioURL: null,
            stopTranscription: false,
            transcription: "",
            rawDataChunks: [],
            currentTimeMinutes: "00",
            currentTimeSeconds: "00",
            currentTimeMilliseconds: "000",
            totalDuration: 0,
            voiceRecord: {
                name: "",
                recording_date: "",
                duration: 0.0,
                type: "audio",
                file: null,
                user_id: null,
                locale: ""
            },


        });
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.setZoomLevel = this.setZoomLevel.bind(this);
        this.wavesurfer = null;
        this.record = null;
        this.waveformRef = useRef("waveform-recorder");
        this.minimapContainer = useRef('minimapContainer');
        this.gridCanvasRef = useRef("gridCanvas");
        this.playbackRef = useRef("playbackContainer");
        this.textareaRef = useRef("textareaRef");
        this.pendingZoomLevel = 10;
        this.recordId = null;
        this.chunkInterval = null;
        this.chunkIntervalTime = 3000;
        this.source = null;
        this.audioContext = null;
        this.processor = null;
        this.connection = null;

        this.mediaStream = null;
        this.voicerecorder = null;

        onWillStart(async () => {
            await loadJS(
                "https://unpkg.com/wavesurfer.js@7.6.4/dist/wavesurfer.min.js"
            );
            await loadJS(
                "https://unpkg.com/wavesurfer.js@7.6.4/dist/plugins/record.min.js"
            );

            await loadJS(
                "https://cdn.jsdelivr.net/npm/howler@2.2.1/dist/howler.min.js"
            );
            await loadJS("https://unpkg.com/peaks.js/dist/peaks.js");
            await loadJS("https://unpkg.com/wavesurfer.js@7.6.4/dist/plugins/regions.min.js");
            await loadJS("https://unpkg.com/wavesurfer.js@7.6.4/dist/plugins/minimap.min.js");
            await loadJS("https://cdn.jsdelivr.net/npm/@deepgram/sdk");


        });
        onMounted(async () => {
            //this.voicerecorder = new VoiceRecorder();
            //this.voicerecorder.audioChunks = [];
            //this.voicerecorder.audioURL = null;
            //console.log("this.voicerecorder", this.voicerecorder);

            this.recordId = this.props.record.data.id;

            try {
                const recordData = await this.orm.call(this.props.record.resModel, "read", [this.recordId], {
                    fields: ['name', 'recording_date', 'duration', 'type', 'file', 'user_id', 'locale'],
                });

                const voiceRecord = await this.rpc('/web/dataset/call_kw', {
                    model: this.props.record.resModel,
                    method: 'read',
                    args: [this.props.record.data.id, ['file']],
                    kwargs: {},
                });
                console.log("voiceRecord", voiceRecord);

                this.syncStateWithRecordData(recordData[0]);
                this.state.voiceRecord.file = voiceRecord[0].file;

                if (voiceRecord[0].file) {
                    // Convert base64 to a Blob
                    //const audioBlob = this.base64ToBlob(recordData[0].file);
                     const audioBlob = this.base64ToBlob(voiceRecord[0].file);
                    // Create an Object URL from the Blob
                    const audioUrl = URL.createObjectURL(audioBlob);
                    // Add the Object URL as the first element of the recordings array
                    this.state.recordings = [{
                        url: audioUrl,
                        duration: recordData[0].duration,
                        rawDataChunks: []
                    }, ...this.state.recordings];

                }
            } catch (error) {
                // this.notification.add('Error loading recording data: ' + error.message, {type: 'danger'});
            }
        });

        onWillUnmount(() => {
            this.cleanupAudioComponents();
        });

        useEffect(() => {

            this.cleanupAudioComponents();
        }, () => [this.props.record.data.id]);
        this.saveRecording = this.saveRecording.bind(this);


    }

    syncStateWithRecordData(recordData) {

        this.state.voiceRecord.name = recordData.name;
        this.state.voiceRecord.recording_date = this.formatDatetime(recordData.recording_date);
        this.state.voiceRecord.duration = recordData.duration;
        this.state.voiceRecord.type = recordData.type;
        //this.state.voiceRecord.file = recordData.file;
        this.state.voiceRecord.user_id = recordData.user_id; // assuming user_id is [id, name_get result]
        this.state.voiceRecord.locale = recordData.locale;
    }

    // Utility function to format Datetime fields
    formatDatetime(value) {
        // Datetime formatting can be adjusted as required.
        return value ? (new Date(value)).toLocaleString() : '';
    }


    createPlayWaveSurfer() {

        if (this.wavesurfer) {
            this.wavesurfer.destroy();
        }
        this.wavesurfer = window.WaveSurfer.create({
            container: this.waveformRef.el,                  // Container element
            height: 120,                                     // Height of the waveform
            "splitChannels": false,
            "normalize": false,
            "waveColor": "#1d45be",
            "progressColor": "#55b9d0",
            "cursorColor": "#bebcbc",
            "cursorWidth": 5,
            "barWidth": 5,
            "barGap": 5,
            "barRadius": null,
            "barHeight": 3.6,
            "barAlign": "",
            "minPxPerSec": 516,
            "fillParent": true,

            "mediaControls": true,
            "autoplay": false,
            "interact": true,
            "dragToSeek": true,
            "hideScrollbar": true,

            "autoScroll": true,
            "autoCenter": true,


        });
        this.wavesurfer.on("ready", () => {
            this.state.totalDuration = this.wavesurfer.getDuration();
        });
        this.wavesurfer.on('timeupdate', (currentTime) => {
            const totalSeconds = Math.floor(currentTime);
            const minutes = Math.floor(totalSeconds / 60);
            const seconds = Math.floor(totalSeconds % 60);
            const millis = Math.floor((currentTime - totalSeconds) * 1000); // Get the milliseconds part

            // Update the currentTime parts in the state
            this.state.currentTimeMinutes = minutes.toString().padStart(2, '0');
            this.state.currentTimeSeconds = seconds.toString().padStart(2, '0');
            this.state.currentTimeMilliseconds = millis.toString().padStart(3, '0');

        });

    }


    createWaveSurfer() {

        if (this.wavesurfer) {
            this.wavesurfer.destroy();
        }
        this.wavesurfer = window.WaveSurfer.create({
            container: this.waveformRef.el,                  // Container element
            height: 120,
            backend: "MediaElement",

            "splitChannels": false,
            "normalize": false,
            "waveColor": "#1d45be",
            "progressColor": "#55b9d0",
            "cursorColor": "#bebcbc",
            "cursorWidth": 5,
            "barWidth": 5,
            "barGap": 5,
            "barRadius": null,
            "barHeight": 3.6,
            "barAlign": "",
            "minPxPerSec": 516,
            "fillParent": true,

            "mediaControls": true,
            "autoplay": false,
            "interact": true,
            "dragToSeek": true,
            "hideScrollbar": true,

            "autoScroll": true,
            "autoCenter": true,


        });


        this.record = this.wavesurfer.registerPlugin(window.WaveSurfer.Record.create({
            renderRecordedAudio: true,

            //mimeType: 'audio/webm;codecs=opus',

            audioChannels: 1,

            //audioBitsPerSecond: 16000
        }));

        this.record.on('record-progress', (milliseconds) => {
            const totalSeconds = Math.floor(milliseconds / 1000);
            const minutes = Math.floor(totalSeconds / 60);
            const seconds = Math.floor(totalSeconds % 60);
            const millis = Math.floor(milliseconds % 1000); // Get the milliseconds part

            // Update the currentTime parts in the state
            this.state.currentTimeMinutes = minutes.toString().padStart(2, '0');
            this.state.currentTimeSeconds = seconds.toString().padStart(2, '0');
            this.state.currentTimeMilliseconds = millis.toString().padStart(3, '0');
            this.state.duration = totalSeconds;
        });


        this.record.on('record-end', (blob) => {
            const recordedUrl = URL.createObjectURL(blob);
            const newRecording = {
                url: recordedUrl,
                duration: this.state.duration,
                rawDataChunks: this.state.rawDataChunks,
            };

            this.state.currentTime = "00:00";
            this.state.recordings.push(newRecording);
        });


        //this.addGridOverlay();

        // Audio constraints
        const constraints = {
            audio: {

                sampleRate: 16000,
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
                //mimeType: 'audio/mp3',
            }
        };

        // Initialize AudioContext and AudioWorklet
        navigator.mediaDevices.getUserMedia(constraints).then(stream => {
            if (!this.audioContext) {
                this.audioContext = new window.AudioContext();
            }
            this.mediaStream = stream; // Store the media stream
            this.source = this.audioContext.createMediaStreamSource(stream);

            // Create a ScriptProcessorNode
            this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);
            this.source.connect(this.processor);
            this.processor.connect(this.audioContext.destination);

            this.processor.onaudioprocess = (e) => {
                // Get the audio chunk data
                const inputBuffer = e.inputBuffer;
                const float32Array = inputBuffer.getChannelData(0); // Assuming mono audio

                // Convert Float32Array to Uint8Array
                const uint8Array = new Uint8Array(float32Array.length);
                for (let i = 0; i < float32Array.length; i++) {
                    // Normalize the float32 value to a value between 0 and 255
                    uint8Array[i] = (float32Array[i] * 0.5 + 0.5) * 255;
                }

                // Store the converted chunk
                this.state.rawDataChunks.push(uint8Array);
                this.state.currentChunk = uint8Array;


                if (this.connection) {
                    // this.connection.send(uint8Array.buffer);
                }

            };


        }).catch(err => {
            console.error('Error accessing the microphone', err);
        });

    }

    addGridOverlay() {
        const canvas = this.gridCanvasRef.el;
        const waveformContainer = this.waveformRef.el;
        const ctx = canvas.getContext("2d");

        canvas.width = waveformContainer.offsetWidth;
        canvas.height = waveformContainer.offsetHeight;

        const gridColor = "rgb(208,208,208)";
        const gridSpacing = 20;

        ctx.strokeStyle = gridColor;
        ctx.lineWidth = 0.7;

        for (let x = 0; x <= canvas.width; x += gridSpacing) {
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, canvas.height);
            ctx.stroke();
        }

        for (let y = 0; y <= canvas.height; y += gridSpacing) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(canvas.width, y);
            ctx.stroke();
        }
    }

    setZoomLevel(event) {
        const newZoomLevel = parseInt(event.target.value, 10);
        if (isNaN(newZoomLevel) || newZoomLevel < 0 || newZoomLevel > 100) {

            return;
        }
        this.state.zoomLevel = newZoomLevel;

        if (this.wavesurfer) {
            this.wavesurfer.zoom(newZoomLevel);
        } else {
            this.pendingZoomLevel = newZoomLevel;
        }
    }

    startRecording = () => {

        this.state.rawDataChunks = []; // Reset chunks
        if (this.chunkInterval) {
            clearInterval(this.chunkInterval);
        }
        if (this.state.isPlaying) {
            this.wavesurfer.stop();
            this.state.isPlaying = false;
        }
        this.createWaveSurfer();
        if (this.record.isRecording() || this.record.isPaused()) {
            return;
        }


        this.state.recordingStatus = 'recording';
        this.state.isRecording = true;
        this.state.duration = 0;
        //this.startDeepgramTranscription();
        this.record.startRecording();


    }

    stopRecording() {
        if (!this.record.isRecording() && !this.record.isPaused()) {
            return;
        }
        this.record.stopRecording();
        this.state.recordingStatus = 'stopped';
        this.state.isRecording = false;
        this.state.isPaused = false;
        this.state.currentTime = "00:00";

        if (this.chunkInterval) {
            clearInterval(this.chunkInterval);
            this.chunkInterval = null;
        }
        if (this.audioContext && this.source && this.processor) {
            console.log("Disconnecting audio context")
            // Disconnect the source from the processor
            this.source.disconnect(this.processor);
            this.processor.disconnect(this.audioContext.destination);

            // Optionally close the AudioContext if it's no longer needed
            this.audioContext.close().then(() => {
                console.log("Audio context closed");
            }); // Success callback


            // Reset the audio context and other related variables
            this.audioContext = null;
            this.source = null;
            this.processor = null;
        }
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }
        if (this.state.recordings.length > 0) {
            const lastRecording = this.state.recordings[this.state.recordings.length - 1];
            lastRecording.rawDataChunks = [...this.state.rawDataChunks];
        }

        // Clear rawDataChunks for the next recording
        this.state.rawDataChunks = [];
        this.stopDeepgramTranscription();

    }

    pauseRecording() {
        if (this.state.recordingStatus === 'recording') {
            this.record.pauseRecording();
            this.state.recordingStatus = 'paused';
            this.state.isPaused = true;
        } else if (this.state.recordingStatus === 'paused') {
            this.record.resumeRecording();
            this.state.recordingStatus = 'recording';
            this.state.isPaused = false;
        }
    }

    cleanupAudioComponents() {
        // If Wavesurfer is currently being used, destroy it and reset related variables
        if (this.wavesurfer) {
            // Stop the currently playing audio, if any
            if (this.wavesurfer.isPlaying()) {
                this.wavesurfer.stop();
            }

            // Destroy the WaveSurfer instance
            this.wavesurfer.destroy();
            this.wavesurfer = null;
        }

        // Stop the media stream (e.g., microphone input) if it is still active
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }

        // Close the AudioContext if it has been created, to free up system resources
        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }

        // Reset processor and source variables that were used for processing audio streams
        this.processor = null;
        this.source = null;

        // Revoke object URLs created for recordings to free up memory and clear recordings from the state
        this.state.recordings.forEach(recording => URL.revokeObjectURL(recording.url));

        // Reset state back to its initial values
        Object.assign(this.state, {
            isRecording: false,
            isPaused: false,
            isPlaying: false,
            zoomLevel: 20, // Maintained, or can be reset to default value
            recordings: [],
            recordingStatus: "stopped",
            playbackInstance: null,
            currentTime: "00:00",
            duration: 0,
            currentSrc: null,
            hasRecording: false,
            audioURL: null,
            stopTranscription: false,
            transcription: "",
            rawDataChunks: [],
            currentTimeMinutes: "00",
            currentTimeSeconds: "00",
            currentTimeMilliseconds: "000",
            totalDuration: 0,
            voiceRecord: {
                name: "",
                recording_date: "",
                duration: 0.0,
                type: "audio",
                file: null,
                user_id: null,
                locale: ""
            },
        });

        // Stop transcription services and cleanup related resources if they are running
        this.stopDeepgramTranscription();

        // Include any additional cleanup logic as required by your application
    }

    getAudioDuration() {
        if (this.wavesurfer) {
            return this.wavesurfer.getDuration();
        } else {

            return 0; // Or handle this situation however appropriate in your context
        }
    }

    togglePlayback() {
        if (this.state.playbackInstance) {
            if (this.state.isPlaying) {
                this.state.playbackInstance.pause();
                this.state.isPlaying = false;
            } else {
                this.playRecording(this.state.recordings[this.state.recordings.length - 1].url);
            }
        }
    }

    playRecording = (url) => {
        if (this.state.isRecording) {
            this.stopRecording();
        }

        // Initialize wavesurfer if it doesn't exist. No need to load URL if it's already playing.
        if (!this.wavesurfer) {
            this.createPlayWaveSurfer();
        }

        if (!this.state.isPlaying) {
            if (this.state.currentSrc !== url) {
                this.wavesurfer.load(url);
                this.wavesurfer.once("ready", () => {
                    this.wavesurfer.play();
                });
            } else {
                this.wavesurfer.play();
            }

            this.state.isPlaying = true;
            this.state.currentSrc = url;
        }

        this.wavesurfer.once("finish", () => {
            this.state.isPlaying = false;
            this.state.currentSrc = null;
        });
    };

    pausePlayback() {
        if (this.state.isPlaying) {
            // Pause the currently playing recording
            this.wavesurfer.pause();
            this.state.isPlaying = false;
        } else {
            // Resume playback from the current position if it's not playing
            this.wavesurfer.play();
            this.state.isPlaying = true;
        }
    }

    stopPlayback() {
        if (this.state.isPlaying && this.state.currentSrc) {
            this.wavesurfer.stop();
            this.state.isPlaying = false;
            this.state.currentSrc = null;
        }
    }

    deleteRecording = (recordingToDelete) => {
        const index = this.state.recordings.indexOf(recordingToDelete);
        if (index > -1) {
            if (this.state.currentSrc === recordingToDelete.url) {
                if (this.state.playbackInstance && this.state.playbackInstance.isPlaying()) {
                    this.state.playbackInstance.stop();
                }
                this.state.currentSrc = null;
            }
            this.state.recordings.splice(index, 1);
            URL.revokeObjectURL(recordingToDelete.url);
        }
    }

    clearTranscription() {

        this.state.stopTranscription = true;
    }

    saveTranscription() {
        console.log("Start Live Transcription :");
        const {createClient} = window.deepgram;

        this.deepgram = createClient('d7172ee47ba2e16a99b48e8d13636f28ad9b835c');
        this.connection = this.deepgram.listen.live({model: "enhanced", language: "fr", punctuate: "true"});
        const url2 = "http://localhost/media_recorder_player/static/AnissaPsy.webm";

        console.log('Deepgram Connection:', this.connection);

        this.connection.on(window.deepgram.LiveTranscriptionEvents.Open, () => {
            console.log("Connection opened.");

            this.connection.on(window.deepgram.LiveTranscriptionEvents.Close, () => {
                console.log("Connection closed.");
            });

            this.connection.on(window.deepgram.LiveTranscriptionEvents.Metadata, (data) => {
                console.log("Metadata:", data);
            });

            this.connection.on(window.deepgram.LiveTranscriptionEvents.Transcript, (data) => {
                console.log("Transcript:", data);
                if (data.is_final) {
                    if (data.channel.alternatives[0].transcript) {
                        this.updateTranscription(data.channel.alternatives[0].transcript);
                    }
                }
            });
            fetch(url2)
                .then((response) => {
                    if (!response.body) {
                        throw new Error('Response body is null');
                    }
                    const reader = response.body.getReader();

                    const readAndSendChunk = () => {
                        reader.read({size: 8000}).then(({done, value}) => {  // Request chunks of 8000 bytes
                            if (done) {
                                console.log('Stream complete');
                                return;
                            }
                            this.connection.send(value);
                            setTimeout(readAndSendChunk, 500); // Send a new chunk every 500ms
                        });
                    };

                    readAndSendChunk();
                })
                .catch((error) => {
                    console.error('Fetch error:', error);
                });

        });
    }

    updateTranscription(transcript) {
        this.state.transcription += transcript + " ";
        this.scrollToBottom()

    }

    scrollToBottom() {
        // Assuming you have a ref to your textarea, e.g., this.textareaRef
        if (this.textareaRef.el) {
            this.textareaRef.el.scrollTop = this.textareaRef.el.scrollHeight;
        }
    }


// Handle the recording of the audio to Odoo backend Save, Load, Update, Detele
    async saveRecording() {


        const latestRecording = this.state.recordings[this.state.recordings.length - 1];
        if (!latestRecording) {
            this.notification.add('No recording available to save.', {type: 'warning'});
            return;
        }

        const blob = await window.fetch(latestRecording.url).then(r => r.blob());
        await this.saveRecordingToServer(blob);


    }

    async saveRecordingToServer(blob) {
        if (!blob) {
            this.notification.add('No recording available to save.', {type: 'warning'});
            return;
        }

        // Use FileReader to convert the Blob to a data URL
        const reader = new FileReader();
        reader.onloadend = async () => {
            try {
                // Extract the Base64 encoded string from the result
                const base64data = reader.result.split(',')[1];
                // Prepare the data to be written to the server

                const uploadValues = {
                    file: base64data, // 'file' should be the name of the binary field in your model
                    duration: this.getAudioDuration(),
                    // Add additional fields as needed, e.g.:
                    name: this.state.voiceRecord.name,
                    // recording_date: this.state.voiceRecord.recording_date, // Ensure the format matches Odoo's expected Datetime format
                    type: this.state.voiceRecord.type,
                    user_id: this.state.voiceRecord.user_id,
                    locale: this.state.voiceRecord.locale,


                    // include other model fields as needed
                };

                // Make the RPC call to write to the voice.recorder model
                await this.rpc("/web/dataset/call_kw", {
                    model: this.props.record.resModel, // Replace with your actual voice recorder model name
                    method: 'write',
                    args: [[this.props.record.data.id], uploadValues], // Replace with the record ID to update
                    kwargs: {},
                });

                this.notification.add('Recording saved successfully.', {type: 'success'});
                // Handle any post-save logic here
            } catch (error) {
                this.notification.add(`Error saving recording: ${error.message}`, {type: 'danger'});
            }
        };

        reader.onerror = () => {
            this.notification.add('Error reading the recording file.', {type: 'danger'});
        };

        reader.readAsDataURL(blob); // Read the Blob object as a data URL
    }

    padBase64(base64String) {
        while (base64String.length % 4 !== 0) {
            base64String += '=';
        }
        // console.log('Padded base64 string:', base64String);
        return base64String;
    }

    base64ToBlob(base64) {
        if (!base64) return null;
        let data = atob(this.padBase64(base64));
        let bytes = new Uint8Array(data.length);
        for (let i = 0; i < data.length; i++) {
            bytes[i] = data.charCodeAt(i);
        }
        // console.log('Converted base64 to Uint8Array:', bytes);
        return new Blob([bytes], {type: 'audio/ogg; codecs=opus'});
    }

    getCurrentChunk() {
        const latestChunk = this.state.rawDataChunks;
        this.state.rawDataChunks = [];
        return latestChunk;
    }

    startDeepgramTranscription() {
        const {createClient} = window.deepgram;


        this.deepgram = createClient('d7172ee47ba2e16a99b48e8d13636f28ad9b835c');
        console.log('Deepgram Instance: ', this.deepgram);
        this.connection = this.deepgram.listen.live({model: "nova-2", language: "fr", punctuate: true});

        this.connection.on(window.deepgram.LiveTranscriptionEvents.Open, () => {
            console.log("Deepgram connection opened.");
        });

        this.connection.on(window.deepgram.LiveTranscriptionEvents.Close, () => {
            console.log("Deepgram connection closed.");
        });

        this.connection.on(window.deepgram.LiveTranscriptionEvents.Metadata, (data) => {
            console.log("Metadata:", data);
        });

        this.connection.on(window.deepgram.LiveTranscriptionEvents.Transcript, (data) => {
            if (data.is_final && data.channel.alternatives[0].transcript) {
                this.updateTranscription(data.channel.alternatives[0].transcript);
            }
        });

        // Continuously send audio chunks to Deepgram
        this.chunkInterval = setInterval(() => {
            if (this.state.rawDataChunks.length > 0) {
                const chunk = this.state.rawDataChunks.shift();
                this.connection.send(chunk);
            }
        }, this.chunkIntervalTime);
    }

    stopDeepgramTranscription() {
        if (this.chunkInterval) {
            clearInterval(this.chunkInterval);
            this.chunkInterval = null;
        }

        if (this.connection) {
            this.connection = null;
        }
    }
}


VoiceRecorderComponent.template = "media_recorder_player.VoiceRecorderComponent";
VoiceRecorderComponent.props = {...standardFieldProps};
VoiceRecorderComponent.supportedTypes = ["binary"];
registry.category("fields").add("recorder", VoiceRecorderComponent);


export default VoiceRecorderComponent;
