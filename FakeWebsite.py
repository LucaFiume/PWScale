from Tester import Tester
import pandas as pd
from Visualizations import PWScalePlotter
import matplotlib.pyplot as plt

class UserInterface:
    def __init__(self):
        self.q = 1

    def ask(self, question):
        print(f'Question #{self.q}: ' + question)
        valid = False
        while not valid:
            answer = input(' Enter 0, 1, 2, 3, or 4: \n')
            try:
                t = int(answer)
                if t in [0, 1, 2, 3, 4]:
                    valid = True
            except:
                valid = False
        self.q += 1
        return int(answer)

    def report(self, p, w):
        print('FINAL RESULTS: P: ' + str(round(p, 3)) + ' - W: ' + str(round(w, 3)))

class FakeWebsite:
    def __init__(self):
        print('WELCOME TO THE ITERATIVE PWSCALE TEST')
        self.name = input('Please enter your full name.\n')

        self.Tester = Tester(UserInterface())

        print('INITIAL SELF-ASSESSMENT')
        self.Tester.self_assessment()

        print('TEST')
        self.Tester.test_core()
        self.Tester.results.to_excel('./Results/PWScale Results ' + self.name + '.xlsx', index=False, float_format="%.3f")
        self.P = self.Tester.P
        self.W = self.Tester.W

f = FakeWebsite()
PWScalePlotter(f.P, f.W).plot_history()
plt.show()