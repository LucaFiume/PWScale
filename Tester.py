import numpy as np
import pandas as pd

class Tester:
    def __init__(self, user_interface, numQs=5, batch=1, loadQs=True):
        self.user_interface = user_interface #User interface to invoke in order to ask questions
        self.batch = batch #This number specifies the number of questions to be selected at once
        self.numQs = numQs #Maximum number of questions for P or W

        if loadQs:
            self.qs = pd.ExcelFile('Questions.xlsx')
            self.SA_questions = pd.read_excel(self.qs, 'SA', index_col=0) #Dataframe with Self-assessment questions
            self.P_questions = pd.read_excel(self.qs, 'P', index_col=0) #Dataframe with P-related questions
            self.W_questions = pd.read_excel(self.qs, 'W', index_col=0) #Dataframe with W-related questions

        self.P = Scale(self.P_questions, batch=batch)
        self.W = Scale(self.W_questions, batch=batch)

        self.results = pd.DataFrame(columns=['Question Number', 'Question', 'Type', 'Lower Bound', 'Higher Bound', 'Answer', 'P Score after', 'W Score after'])

    def self_assessment(self):
        """This function starts with the self-assessment part of the test, updating the user's P/W scores accordingly"""
        for i in range(len(self.SA_questions)):
            question = self.SA_questions.iloc[i]['Question']
            scale = self.SA_questions.iloc[i]['P/W']
            weight = self.SA_questions.iloc[i]['Weight']

            #There has to be a coordination between the question database and the class Scale definition. Both have to work with the same scale!
            lowbound = self.SA_questions.iloc[i]['Very Uncomfortable']
            highbound = self.SA_questions.iloc[i]['Very Comfortable']

            # The user interface now asks the user the question, and returns the value between lowbound and highbound
            # corresponding to the user's answer
            answer = self.user_interface.ask(question)

            if scale == 'P':
                self.P.update_score(answer, weight, lowbound, highbound)
                type = 'SA - P'
            else:
                self.W.update_score(answer, weight, lowbound, highbound)
                type = 'SA - W'

            self.results = self.results.append(
                {'Question Number': len(self.results) + 1, 'Question': question, 'Type': type, 'Lower Bound': lowbound,
                 'Higher Bound': highbound, 'Answer': np.linspace(lowbound, highbound, 5)[answer], 'P Score after': self.P.score,
                 'W Score after': self.W.score}, ignore_index=True)

    def test_core(self, check_convergence=10):
        """Dynamic part of the test. check_convergence indicates after which question should convergence be checked"""
        for i, isP in enumerate([True, False] * self.numQs):
            if isP:
                if not self.P.converged:
                    next = self.P.next_question()
                    question, weight, lowbound, highbound = self.P.question_info(next)
                    answer = self.user_interface.ask(question)
                    self.P.update_score(answer, weight, lowbound, highbound)

                    if i > check_convergence:
                        self.P.check_convergence()
                    type = 'P'
            else:
                if not self.W.converged:
                    next = self.W.next_question()
                    question, weight, lowbound, highbound = self.W.question_info(next)
                    answer = self.user_interface.ask(question)
                    self.W.update_score(answer, weight, lowbound, highbound)
                    if i > check_convergence:
                        self.W.check_convergence()
                    type = 'W'

            if not(self.W.converged) or not(self.P.converged):
                self.results = self.results.append(
                    {'Question Number': len(self.results) + 1, 'Question': question, 'Type': type, 'Lower Bound': lowbound,
                     'Higher Bound': highbound, 'Answer': np.linspace(lowbound, highbound, 5)[answer], 'P Score after': self.P.score,
                     'W Score after': self.W.score}, ignore_index=True)

        self.user_interface.report(self.P.score, self.W.score)


class Scale:
    """This simple class is made to store the information regarding each of the two scales in an efficient way, no need
    to repeat the same code for each scale"""
    def __init__(self, questions, batch=1, bounds=[-100, 100], battery=10):
        #Dataframe of questions relative to the scale
        self.questions = questions
        #Number of questions to be asked at once
        self.batch = batch
        # List of answers, containing the P/W scale value of each answer
        self.answers = []
        # List of question IDs, containing the answered questions for each of the scales
        self.answered = []
        # List of answered question weights, for each of the scales
        self.weights = []
        # Initial Scores
        self.score = 0
        # History of Scores for each of the scales
        self.history = []
        # Waiting list of questions to be asked next
        self.next = []
        #Boolean indicating if the scale value has converged to a particular value
        self.converged = False
        #Bounds of the scale to be implemented
        self.bounds = bounds
        #Length of initial battery of questions
        self.battery = battery

    def update_score(self, answer, weight, lowbound, highbound):
        """This generic function is in charge of updating the user's current P or W score, taking into account all previous
        answers and their respective weights.
        answer: integer in [0, 1, 2, 3, 4], representing the user's latest answer
        weight: float representing the weight of the last question answered
        lowbound: Scale value of the answer corresponding to a 0
        highbound: Scale value of the answer corresponding to a 4"""

        answer = np.linspace(lowbound, highbound, 5)[answer]
        result = 0
        self.answers.append(answer)
        self.weights.append(weight)
        for i, ans in enumerate(self.answers):
            result += ans * self.weights[i]
        result = result / sum(self.weights)
        self.score = result
        self.history.append(result)

    def next_question(self):
        """This function finds the question most suited for the current score"""
        if len(self.next) == 0:
            adequacy = self.questions['Suited for'].drop(self.answered)
            ranking = np.argsort(np.abs(adequacy.values - self.score))

            if len(ranking) > self.batch:
                self.next = list(adequacy.index[ranking[0:self.batch]].values)
            elif len(ranking) > 0:
                self.next = list(adequacy.index[ranking].values)
            else:
                print('ERROR: No questions remain.')
                self.converged = True
                self.next = [None]

        next = self.next[0] #Immediately next question
        self.next.pop(0)
        return next

    def question_info(self, qid):
        """This function returns the question info associated with the question ID in qid"""
        question = self.questions.loc[qid]['Question']
        weight = self.questions.loc[qid]['Weight']
        lowbound = self.questions.loc[qid]['Very Uncomfortable']
        highbound = self.questions.loc[qid]['Very Comfortable']
        self.answered.append(qid)
        return question, weight, lowbound, highbound

    def check_convergence(self, tol=100, deltaMu=50, deltaSigma=50):
        """Here, the three existing convergence criteria are checked at the same time, with the three tolerance parameters
        set as an input. If all three criteria are satisfied, it is said that the score has converged."""

        score_converged = self.check_score_convergence(tol)
        delta_mean_converged = self.check_delta_mean(deltaMu)
        delta_std_converged = self.check_delta_std(deltaSigma)
        if score_converged and delta_mean_converged and delta_std_converged:
            self.converged = True

    def check_score_convergence(self, tolerance=0.1, relative=False):
        """This function checks the history of scale values, and based on the two last values, establishes whether the
        evolution of the scale value has converged to a particular value. For the input:
        tolerance: Float representing the tolerance to be surpassed between adjacent scores to not establish convergence
        relative: Boolean establishing whether the tolerance is computed as a percentage of the first value in the sequence
        or as an absolute value."""

        score_converged = False
        if len(self.history) > 1:
            if relative:
                dev = abs(self.history[-1] - self.history[-2]) / abs(self.history[-2])
            else:
                dev = abs(self.history[-1] - self.history[-2])

            if dev > tolerance:
                score_converged = True
        return score_converged

    def check_delta_mean(self, delta=0.5):
        """This function checks the deviation existing between the score of the user's last answered question and the user's
        score before such question. If the deviation is above the input float delta, it is said that the user's delta is
        that of a converged test."""

        delta_mean_converged = False
        if len(self.history) > 1:
            dev = abs(self.answers[-1] - self.history[-2])
            if dev > delta:
                delta_mean_converged = True
        return delta_mean_converged

    def check_delta_std(self, delta=0.5):
        """This function checks the deviation existing between the standard deviation of answers provided during the initial
        battery/SA and the standard deviation of answers provided after such part of the test. If the deviation is above
        the input float delta, it is said that the user's delta is that of a converged test."""

        delta_std_converged = False
        if len(self.answers) > self.battery:
            stdSA = np.std(self.answers[:self.battery])
            stdAfter = np.std(self.answers[self.battery:])
            dev = abs(stdSA - stdAfter)
            if dev > delta:
                delta_std_converged = True
        return delta_std_converged

class Mapper:
    def __init__(self, frontBounds=[1,4], frontValues=7, backBounds=[-100, 100]):
        """This auxiliary class is used for all mapping from a scale used in the backend of the calculations, defined by
        the bounds contained in backBounds, and an exterior scale which is presented to the user. This latter scale is
        contained within the bounds presented in frontBounds and has as many values as introduced in frontValues."""
        self.frontBounds = frontBounds
        self.frontValues = np.linspace(frontBounds[0], frontBounds[1], frontValues)
        self.backBounds = backBounds

        #Since both scales are linear, one can introduce here the two coefficients with which a value is converted from one scale to the other.
        self.f2b = {'Slope': (backBounds[1] - backBounds[0]) / (frontBounds[1] - frontBounds[0]), 'Add': backBounds[0] - ((backBounds[1] - backBounds[0]) * frontBounds[0] / (frontBounds[1] - frontBounds[0]))}
        self.b2f = {'Slope': (frontBounds[1] - frontBounds[0]) / (backBounds[1] - backBounds[0]), 'Add': frontBounds[0] - ((frontBounds[1] - frontBounds[0]) * backBounds[0] / (backBounds[1] - backBounds[0]))}

    def front_to_back(self, x):
        """Here, values in x, expressed in the frontend scale, are converted to the backend scale."""
        try:
            #x is an iterable
            if max(x) > self.frontBounds[1] or min(x) < self.frontBounds[0]:
                print("ERROR: Values to be converted to the backend scale are beyond the frontend scale's bounds")
        except:
            # x is not an iterable
            if x > self.frontBounds[1] or x < self.frontBounds[0]:
                print("ERROR: Values to be converted to the backend scale are beyond the frontend scale's bounds")

        y = x * self.f2b['Slope'] + self.f2b['Add']
        return y

    def back_to_front(self, x):
        """Here, values in x, expressed in the backend scale, are converted to the frontend scale."""
        try:
            #x is an iterable
            if max(x) > self.backBounds[1] or min(x) < self.backBounds[0]:
                print("ERROR: Values to be converted to the frontend scale are beyond the backend scale's bounds")

            y = x * self.b2f['Slope'] + self.b2f['Add']
            clamped = np.zeros((len(y), 1))
            for i ,v in enumerate(y):
                closest = np.argmin(abs(self.frontValues - v))
                clamped[i] = self.frontValues[closest]
        except:
            # x is not an iterable
            if x <= self.backBounds[1] and x >= self.backBounds[0]:
                print("ERROR: Values to be converted to the frontend scale are beyond the backend scale's bounds")

            y = x * self.b2f['Slope'] + self.b2f['Add']
            closest = np.argmin(abs(self.frontValues - y))
            clamped = self.frontValues[closest]

        return clamped

    def which_scale(self, x):
        """This function makes uses of the bounds of each scale in order to state if the values of x belong to the
        backend scale or to the frontend scale. Throughout this function, 0 means the backend, 1 means the frontend"""

        left_widest = np.argmin([self.backBounds[0], self.frontBounds[0]])
        left_tightest = np.argmax([self.backBounds[0], self.frontBounds[0]])
        right_widest = np.argmax([self.backBounds[1], self.frontBounds[1]])
        right_tightest = np.argmin([self.backBounds[1], self.frontBounds[1]])

        try:
            top = max(x)
            low = min(x)
        except:
            top = x
            low = x

        if low < np.max([self.backBounds[0], self.frontBounds[0]]):
            left_says = left_widest
        else:
            left_says = left_tightest
        if top > np.min([self.backBounds[1], self.frontBounds[1]]):
            right_says = right_widest
        else:
            right_says = right_tightest

        if right_says == left_says:
            scale = right_says
        else:
            print('ERROR: Values to be detected are ambiguous')
            scale = None
        return scale
