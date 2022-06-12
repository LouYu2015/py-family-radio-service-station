# Channels to listen
CHANNELS = [462.625e6, 462.725e6]
# Offset the center frequency to avoid the spike in center frequency
F_OFFSET = 250e3
# Window size of the frequency filter
FILTER_WINDOW = 201
# Bandwidth of each channel
F_BANDWIDTH = 12.5e3
# Buffer time per audio block
BUFFER_TIME = 0.1
# Wait for SIGNAL_WAIT_TIME * BUFFER_TIME of silence before switching channels
SIGNAL_WAIT_TIME = 2
# Multiply output audio by this volume
VOLUME = 20

# Here is a list of all FRS channels
# CHANNELS = [
#     462.5625e6,
#     462.5875e6,
#     462.6125e6,
#     462.6375e6,
#     462.6625e6,
#     462.6875e6,
#     462.7125e6,
#     467.5625e6,
#     467.5875e6,
#     467.6125e6,
#     467.6375e6,
#     467.6625e6,
#     467.6875e6,
#     467.7125e6,
#     462.5500e6,
#     462.5750e6,
#     462.6000e6,
#     462.6250e6,
#     462.6500e6,
#     462.6750e6,
#     462.7000e6,
#     462.7250e6,
# ]
