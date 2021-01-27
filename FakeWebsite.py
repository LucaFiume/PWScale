from Tester import Tester
import pandas as pd
from Visualizations import PWScalePlotter
import matplotlib.pyplot as plt


class Asker:
    def __init__(self):
        self.q = 1

    def ask(self, questions, continuous=False):
        if type(questions) != list:
            questions = [questions]

        answers = []

        for q in questions:
            print(f'Question #{self.q}: ' + q)
            valid = False
            answer = 9
            while not valid:
                if continuous:
                    answer = input(' Enter a number from 0 to 10: \n')
                    answer = float(answer)
                else:
                    answer = input(' Enter 0, 1, 2, 3, or 4: \n')

                try:
                    if continuous and 0 <= answer <= 10:
                        valid = True
                    elif not continuous:
                        t = int(answer)
                        if t in [0, 1, 2, 3, 4]:
                            valid = True
                except TypeError:
                    valid = False
            self.q += 1
            if continuous:
                answers.append(answer)
            else:
                answers.append(int(answer))
        return answers

    @staticmethod
    def report(p, w):
        print('FINAL RESULTS: P: ' + str(round(p, 3)) + ' - W: ' + str(round(w, 3)))


class FakeWebsite:
    # This class should be the one calling the asker function
    def __init__(self, asker):
        print('WELCOME TO THE ITERATIVE PWSCALE TEST')
        # self.name = input('Please enter your full name.\n')
        self.name = 'test'
        self.qs = pd.ExcelFile('Questions.xlsx', engine='openpyxl')

        cols = ['Question ID', 'Question']
        # Dataframe with Self-assessment questions
        self.questions = pd.read_excel(self.qs, 'self_assessment_questions')
        # Dataframe with P-related questions
        self.questions = self.questions[cols].append(pd.read_excel(self.qs, 'P')[cols], ignore_index=True)
        # Dataframe with W-related questions
        self.questions = self.questions[cols].append(pd.read_excel(self.qs, 'W')[cols], ignore_index=True)

        self.tester = Tester(store_results=True)

        # CONNECTION WITH THE BACKEND: Extract questions to be asked
        print('INITIAL SELF-ASSESSMENT')
        to_ask = self.tester.self_assessment_emmit()

        # CONNECTION WITH FRONTEND: to_ask is a list of Question IDs to be asked
        questions = self.get_questions(to_ask)
        answers = asker.ask(questions)

        # CONNECTION WITH THE BACKEND: answers is a list of integers in [0, 1, 2, 3, 4]
        _, _ = self.tester.receive(answers, to_ask, is_self_assessment=True)

        print('TEST')
        done = False
        while not done:
            # CONNECTION WITH THE BACKEND: Extract questions to be asked
            to_ask, done = self.tester.test_core_emmit()

            # CONNECTION WITH FRONTEND: to_ask is a list of Question IDs to be asked, done is a boolean indicating
            # convergence
            if len(to_ask) > 0:
                questions = self.get_questions(to_ask)
                answers = asker.ask(questions)

                # CONNECTION WITH THE BACKEND: answers is a list of integers in [0, 1, 2, 3, 4]
                self.tester.receive(answers, to_ask)

        # CONNECTION WITH THE BACKEND: Extract questions to be asked
        print('VIDEOS')
        to_ask = self.tester.video_emmit()

        # CONNECTION WITH FRONTEND: to_ask is a list of Question IDs to be asked
        questions = to_ask
        answers = asker.ask(questions, continuous=True)

        # CONNECTION WITH THE BACKEND: now, answers is a list of integers from 0 to 10
        p_score, w_score = self.tester.receive(answers, to_ask, is_video=True)

        asker.report(p_score, w_score)
        self.tester.results.save(self.name)
        self.P = self.tester.P
        self.W = self.tester.W

    def get_questions(self, question_ids, with_type=True):
        qs = []
        for q in question_ids:
            mask = self.questions['Question ID'] == q
            if with_type:
                qs.append('(' + q + ') ' + self.questions.loc[mask, ['Question']].values[0][0])
            else:
                qs.append(self.questions.loc[mask, ['Question']].values[0][0])
        return qs


f = FakeWebsite(Asker())
PWScalePlotter(f.P, f.W).plot_history_separated()
plt.show()
