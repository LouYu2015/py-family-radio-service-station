import multiprocessing
import asyncio
import queue
import time
import faulthandler
from rtlsdr import RtlSdr
import numpy as np
import scipy.signal as signal
import sounddevice as sd
import config
import gui


# Plays FM radio through the computer audio output.

faulthandler.enable()
exitFlag = multiprocessing.Event()  # set flag to exit by pressing ESC
sample_queue = multiprocessing.Queue()  # samples added to the queue for processing
audio_queues = [multiprocessing.Queue() for _ in config.CHANNELS]  # audio added to the queue to be played


# Handles sampling, processing, and playing from an SDR
# Outputs audio samples to Radio.output_queue for potential use by other programs
# Optional contructor arguments:
#   # sdr sampling rate, must be a multiple of 256
#   # audio sampling rate
#   # sdr listening frequency
#   # sdr tuning offset
#   # buffer time
class Radio:
    def __init__(self, f_sps=1.0*256*256*16, f_audiosps=48000, f_c=config.CHANNELS[0], buffer_time=config.BUFFER_TIME):
        self.ui = None

        # set up constants
        self.f_sps = f_sps  # sdr sampling frequency
        self.f_audiosps = f_audiosps  # audio sampling frequency (for output)
        self.f_c = f_c  # listening frequency
        self.buffer_time = buffer_time  # length in seconds of samples in each buffer
        self.N = round(self.f_sps*self.buffer_time)  # number of samples to collect per buffer

        # initialize multiprocessing processes
        self.sample_process = SampleProcess(exitFlag, self.f_sps, self.f_c, self.N, sample_queue)
        self.extraction_process = ExtractionProcess(exitFlag, self.f_sps, self.f_audiosps, sample_queue, audio_queues)

        # initalize output audio stream
        self.stream = sd.OutputStream(samplerate=self.f_audiosps, blocksize=int(self.N / (self.f_sps / self.f_audiosps)), channels=1)

        self.output_queue = multiprocessing.Queue(25)  # for other programs to use audio samples. max size is 25 to avoid memory overuse if output is not being used.

        print('\nInitialized. Starting streaming. Press <ESC> to exit.\n')
        self.stream.start()
        # self.exit_listener.start()
        self.sample_process.start()
        self.extraction_process.start()

        self.current_channel = 0
        self.ui = gui.GUI(destroy_callback=self.cleanup)
        self.next_audio()
    
    def next_audio(self):
        audio = None

        for channel, audio_queue in enumerate(audio_queues):
            if audio_queue.empty():
                self.ui.set_channel_activity(channel, 'nothing')
            else:
                self.ui.set_channel_activity(channel, 'waiting')

        try:
            audio = audio_queues[self.current_channel].get(block=True, timeout=2 * config.BUFFER_TIME)
        except queue.Empty:
            for channel, audio_queue in enumerate(audio_queues):
                try:
                    audio = audio_queue.get(block=False)
                    self.current_channel = channel
                except queue.Empty:
                    pass
            if audio is None:
                self.ui.window.after(int(1000 * config.BUFFER_TIME / 2), self.next_audio)
                return
        audio = audio.astype(np.float32)

        # play audio and send to output queue if it's not full
        try:
            self.ui.set_channel_activity(self.current_channel, 'active')
            self.output_queue.put(audio, block=False)
        except queue.Full:
            pass

        self.stream.write(config.VOLUME * audio)
        self.ui.window.after(int(1000 * config.BUFFER_TIME), self.next_audio)

    def cleanup(self):
        time.sleep(self.buffer_time)  # wait to allow processes to finish
        exitFlag.set()
        self.extraction_process.join()
        self.sample_process.terminate()
        self.sample_process.join()
        sample_queue.close()
        for audio_queue in audio_queues:
            audio_queue.close()
        self.stream.stop()
        self.stream.close()

    # def on_press(self, key):
    #     if key == keyboard.Key.esc:
    #         exitFlag.set()
    #         self.cleanup()


# Process to sample radio using the sdr
class SampleProcess(multiprocessing.Process):
    def __init__(self, exitFlag, f_sps, f_c, buffer_length, sample_queue):
        multiprocessing.Process.__init__(self)
        self.exitFlag = exitFlag
        self.f_sps = f_sps
        self.f_c = f_c
        self.buffer_length = buffer_length
        self.sample_queue = sample_queue

    def run(self):
        asyncio.run(self.stream_samples(self.buffer_length, self.f_sps, self.f_c))

    async def stream_samples(self, N, f_sps, f_c):
        # initialize SDR
        sdr = RtlSdr()
        sdr.sample_rate = f_sps
        sdr.center_freq = f_c + config.F_OFFSET
        sdr.gain = -1.0  # increase for receiving weaker signals. valid gains (dB): -1.0, 1.5, 4.0, 6.5, 9.0, 11.5, 14.0, 16.5, 19.0, 21.5, 24.0, 29.0, 34.0, 42.0
        samples = np.array([], dtype=np.complex64)
        async for sample_set in sdr.stream():  # streams 131072 samples at a time
            samples = np.concatenate((samples, sample_set))
            if len(samples) >= N:
                self.sample_queue.put(samples)
                samples = np.array([], dtype=np.complex64)
            
            if exitFlag.is_set():
                return True


# Process to extract audio from the samples
class ExtractionProcess(multiprocessing.Process):
    def __init__(self, exitFlag, f_sps, f_audiosps, sample_queue, audio_queues):
        self.exitFlag = exitFlag
        multiprocessing.Process.__init__(self)
        self.f_sps = f_sps
        self.f_audiosps = f_audiosps
        self.shift_operators = None
        self.firtaps = signal.firwin(config.FILTER_WINDOW, cutoff=config.F_BANDWIDTH,
                                     fs=f_sps, window='hamming')
        self.sample_queue = sample_queue
        self.audio_queues = audio_queues

    def run(self):
        while not self.exitFlag.is_set():
            try:
                samples = self.sample_queue.get(block=True, timeout=2 * config.BUFFER_TIME)
            except queue.Empty:
                continue
            filteredsignals = self.filter_samples(samples, self.f_sps)
            audios = [self.process_signal(filteredsignal, self.f_sps, self.f_audiosps)
                      for filteredsignal in filteredsignals]
            for channel, (audio, filteredsignal) in enumerate(zip(audios, filteredsignals)):
                power = np.mean(np.abs(filteredsignal))
                # print(channel, power)
                if power > 0.1:
                    self.audio_queues[channel].put(audio, block=False)

    # returns filtered signal
    def filter_samples(self, samples, f_sps):
        if self.shift_operators is None:
            n = len(samples)
            self.shift_operators = [
                np.exp(1.0j * 2.0 * np.pi * -(channel - config.CHANNELS[0] - config.F_OFFSET) / f_sps * np.arange(n))
                for channel in config.CHANNELS]

        # shift samples back to center frequency using complex exponential with period f_offset/f_sps
        shifted_samples = [samples * operator for operator in self.shift_operators]

        # filter samples to include only the FM bandwidth
        filteredsignals = [np.convolve(self.firtaps, shifted_sample, mode='same')
                           for shifted_sample in shifted_samples]

        return filteredsignals
    
    # returns audio processed from filteredsignal
    def process_signal(self, filteredsignal, f_sps, f_audiosps):
        theta = np.arctan2(filteredsignal.imag, filteredsignal.real)

        # squelch low power signal to remove noise
        abssignal = np.abs(filteredsignal)
        meanabssignal = np.mean(abssignal)
        theta = np.where(abssignal < meanabssignal / 3, 0, theta)

        # calculate derivative of phase (instantaneous frequency)
        # and unwrap phase-wrapping effects
        derivtheta = np.diff(np.unwrap(theta) / (2 * np.pi))

        # downsample by taking average of surrounding values
        dsf = round(f_sps/f_audiosps)  # downsampling factor
        # pad derivtheta with NaN so size is divisible by dsf, then split into rows of size dsf and take the mean of each row
        derivtheta_padded = np.pad(derivtheta.astype(float), (0, dsf - derivtheta.size % dsf), mode='constant', constant_values=np.NaN)
        dsdtheta = np.nanmean(derivtheta_padded.reshape(-1, dsf), axis=1)

        return dsdtheta


if __name__ == '__main__':
    r = Radio(buffer_time=config.BUFFER_TIME)
    r.ui.mainloop()
