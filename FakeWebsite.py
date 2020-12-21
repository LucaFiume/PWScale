from Tester import Tester
import pandas as pd
from Visualizations import PWScalePlotter
import matplotlib.pyplot as plt

class Asker:
    def __init__(self):
        self.q = 1

    def ask(self, questions):
        if type(questions) != list:
            questions = [questions]

        answers = []

        for q in questions:
            print(f'Question #{self.q}: ' + q)
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
            answers.append(int(answer))
        return answers

    def report(self, p, w):
        print('FINAL RESULTS: P: ' + str(round(p, 3)) + ' - W: ' + str(round(w, 3)))

class FakeWebsite: #This class should be the one calling the asker function
    def __init__(self, Asker):
        print('WELCOME TO THE ITERATIVE PWSCALE TEST')
        # self.name = input('Please enter your full name.\n')
        self.name = 'test'
        self.qs = pd.ExcelFile('Questions.xlsx')

        cols = ['Question ID', 'Question']
        self.questions = pd.read_excel(self.qs, 'SA')  # Dataframe with Self-assessment questions
        self.questions = self.questions[cols].append(pd.read_excel(self.qs, 'P')[cols], ignore_index=True)  # Dataframe with P-related questions
        self.questions = self.questions[cols].append(pd.read_excel(self.qs, 'W')[cols], ignore_index=True)  # Dataframe with W-related questions

        self.Tester = Tester()

        # CONNECTION WITH THE BACKEND: Extract questions to be asked
        print('INITIAL SELF-ASSESSMENT')
        toAsk = self.Tester.self_assessment_emmit()

        # CONNECTION WITH FRONTEND: toAsk is a list of Question IDs to be asked
        questions = self.get_questions(toAsk)
        answers = Asker.ask(questions)

        # CONNECTION WITH THE BACKEND: answers is a list of integers in [0, 1, 2, 3, 4]
        _, _ = self.Tester.receive(answers, toAsk, isSA=True)

        print('TEST')
        done = False
        previousType = 'W' #This is used in order to make sure that P and W questions are asked in alternating order
        i = 1 #This is needed in the backend in order to keep count of the questions
        while not(done):
            # CONNECTION WITH THE BACKEND: Extract questions to be asked
            toAsk, done = self.Tester.test_core_emmit(previousType, i)

            # CONNECTION WITH FRONTEND: toAsk is a list of Question IDs to be asked, done is a boolean indicating convergence
            if len(toAsk) > 0:
                previousType = toAsk[-1][0]
                questions = self.get_questions(toAsk)
                answers = Asker.ask(questions)

                # CONNECTION WITH THE BACKEND: answers is a list of integers in [0, 1, 2, 3, 4]
                _, _ = self.Tester.receive(answers, toAsk, i)
                i += 1

        # CONNECTION WITH THE BACKEND: Extract questions to be asked
        print('VIDEOS')
        toAsk = self.Tester.video_emmit()

        # CONNECTION WITH FRONTEND: toAsk is a list of Question IDs to be asked
        questions = toAsk
        answers = Asker.ask(questions)

        # CONNECTION WITH THE BACKEND: answers is a list of integers in [0, 1, 2, 3, 4]
        P_score, W_score = self.Tester.receive(answers, toAsk, isVideo=True)

        Asker.report(P_score, W_score)
        self.Tester.results.save(self.name)
        self.P = self.Tester.P
        self.W = self.Tester.W

    def get_questions(self, QIDs, withType=True):
        qs = []
        for q in QIDs:
            mask = self.questions['Question ID'] == q
            if withType:
                qs.append('(' + q + ') '+ self.questions.loc[mask, ['Question']].values[0][0])
            else:
                qs.append(self.questions.loc[mask, ['Question']].values[0][0])
        return qs

f = FakeWebsite(Asker())
PWScalePlotter(f.P, f.W).plot_history_separated()
plt.show()