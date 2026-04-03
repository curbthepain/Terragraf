"""
.scaffold/viz/stream.py
Real-time data stream plotter — scrolling line charts, live updates.

Provides:
  - StreamPlotter — animated scrolling line chart
"""

import numpy as np
from collections import deque


class StreamPlotter:
    """
    Real-time scrolling data plotter.

    Usage:
        plotter = StreamPlotter(window=200, n_lines=2, labels=["signal", "filtered"])
        plotter.start()
        for sample in data_stream:
            plotter.update([sample.raw, sample.filtered])
        plotter.stop()
    """

    def __init__(self, window=200, n_lines=1, labels=None,
                 title="Live Stream", figsize=(10, 4), interval=50):
        """
        window:   number of samples visible at once
        n_lines:  number of data channels
        labels:   list of channel names
        interval: update interval in ms
        """
        self.window = window
        self.n_lines = n_lines
        self.labels = labels or [f"ch{i}" for i in range(n_lines)]
        self.title = title
        self.figsize = figsize
        self.interval = interval
        self.buffers = [deque(maxlen=window) for _ in range(n_lines)]
        self._fig = None
        self._ax = None
        self._lines = None
        self._anim = None

    def start(self):
        """Initialize the plot and start the animation loop."""
        import matplotlib.pyplot as plt
        from matplotlib.animation import FuncAnimation

        self._fig, self._ax = plt.subplots(1, 1, figsize=self.figsize)
        self._ax.set_title(self.title)
        self._ax.set_xlim(0, self.window)
        self._ax.set_ylim(-1, 1)

        self._lines = []
        for i in range(self.n_lines):
            line, = self._ax.plot([], [], label=self.labels[i])
            self._lines.append(line)
        self._ax.legend(loc="upper right")

        self._anim = FuncAnimation(
            self._fig, self._animate, interval=self.interval, blit=True
        )
        plt.show(block=False)

    def update(self, values):
        """
        Push new data point(s).
        values: list/array of length n_lines, one value per channel.
        """
        for i, v in enumerate(values):
            self.buffers[i].append(v)

    def _animate(self, frame):
        for i, line in enumerate(self._lines):
            data = list(self.buffers[i])
            line.set_data(range(len(data)), data)

        # Auto-scale y axis
        all_data = []
        for buf in self.buffers:
            all_data.extend(buf)
        if all_data:
            ymin, ymax = min(all_data), max(all_data)
            margin = max(0.1, (ymax - ymin) * 0.1)
            self._ax.set_ylim(ymin - margin, ymax + margin)

        return self._lines

    def stop(self):
        """Stop the animation and close the figure."""
        import matplotlib.pyplot as plt
        if self._anim:
            self._anim.event_source.stop()
        if self._fig:
            plt.close(self._fig)
