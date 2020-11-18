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
        ax.set_ylim(-110, 110)
        ax.tick_params(axis='y', labelsize=18, labelcolor=color)
        ax.plot(np.arange(len(self.P.history)) + 1, self.P.history, marker='o', color=color, label=None)
        ax.plot(np.arange(len(self.P.history)) + 1, self.P.history, color=color, label=None)

        ax2 = ax.twinx()
        color = 'tab:blue'
        ax2.set_ylabel('W Scale [-]', fontsize=20, color=color)
        ax2.set_ylim(-110, 110)
        ax2.tick_params(axis='y', labelsize=18, labelcolor=color)
        ax2.plot(np.arange(len(self.W.history)) + 1, self.W.history, marker='o', color=color)
        ax2.plot(np.arange(len(self.W.history)) + 1, self.W.history, color=color)

        legempty = True
        critNames = ['Average Score Converged', 'Deviation from Score is Small', 'Std Deviation is Equal to that of Self-Assessment']
        scNames = ['P', 'W']
        for j, scale in enumerate([self.P, self.W]):
            for i, n in enumerate(critNames):
                if scale.criteria[i] > 0:
                    x = scale.criteria[i] * np.ones((50, 1))
                    y = np.linspace(-110, 100, 50)
                    ax.plot(x, y, label=scNames[j] + ' - ' + n)
                    legempty = False

        if not legempty:
            ax.legend(fontsize=18)
