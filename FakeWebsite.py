from Tester import Tester
import pandas as pd

class UserInterface:
    def __init__(self):
        self.q = 1

    def ask(self, question):
        print(f'Question #{self.q}: ' + question)
        answer = input(' Enter 0, 1, 2, 3, or 4: \n')
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

FakeWebsite()