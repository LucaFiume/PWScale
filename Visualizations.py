import matplotlib.pyplot as plt
import numpy as np

class PWScalePlotter:
    def __init__(self, P, W):
        self.P = P
        self.W = W

    def plot_history(self):
        fig, ax = plt.subplots()
        fig.set_size_inches(16, 10)
        ax.set_xlabel('Question Number [-]', fontsize=24)
        ax.set_title('Evolution PW Scores with Test', fontsize=24)
        ax.grid(True)

        color = 'tab:red'
        ax.set_ylabel('P Scale [-]', fontsize=20, color=color)
        ax.set_ylim(1, 4)
        ax.tick_params(axis='y', labelsize=18, labelcolor=color)
        ax.plot(self.P.history, marker='o', color=color)
        ax.plot(self.P.history, color=color)

        ax2 = ax.twinx()
        color = 'tab:blue'
        ax2.set_ylabel('W Scale [-]', fontsize=20, color=color)
        ax2.set_ylim(1, 4)
        ax2.tick_params(axis='y', labelsize=18, labelcolor=color)
        ax2.plot(self.W.history, marker='o', color=color)
        ax2.plot(self.W.history, color=color)

