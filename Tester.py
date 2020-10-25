import numpy as np
import pandas as pd

class Tester:
    def __init__(self, user_interface, numQs=5, batch=1, loadQs=True):
        self.user_interface = user_interface #User interface to invoke in order to ask questions
        self.batch = batch #This number specifies the number of questions to be selected at once
        self.numQs = numQs #Number of questions for P or W

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

    def test_core(self):
        for i, isP in enumerate([True, False] * self.numQs):
            if isP:
                next = self.P.next_question()
                question, weight, lowbound, highbound = self.P.question_info(next)
                answer = self.user_interface.ask(question)
                self.P.update_score(answer, weight, lowbound, highbound)
                type = 'P'
            else:
                next = self.W.next_question()
                question, weight, lowbound, highbound = self.W.question_info(next)
                answer = self.user_interface.ask(question)
                self.W.update_score(answer, weight, lowbound, highbound)
                type = 'W'

            self.results = self.results.append(
                {'Question Number': len(self.results) + 1, 'Question': question, 'Type': type, 'Lower Bound': lowbound,
                 'Higher Bound': highbound, 'Answer': np.linspace(lowbound, highbound, 5)[answer], 'P Score after': self.P.score,
                 'W Score after': self.W.score}, ignore_index=True)

        self.user_interface.report(self.P.score, self.W.score)


class Scale:
    """This simple class is made to store the information regarding each of the two scales in an efficient way, no need
    to repeat the same code for each scale"""
    def __init__(self, questions, batch=1):
        #Dataframe of questions relative to the scale
        self.questions = questions
        #Number of questions to be asked at once
        self.batch = 1
        # List of answers, containing the P/W scale value of each answer
        self.answers = []
        # List of question IDs, containing the answered questions for each of the scales
        self.answered = []
        # List of answered question weights, for each of the scales
        self.weights = []
        # Initial Scores
        self.score = 2.5
        # History of Scores for each of the scales
        self.history = []
        # Waiting list of questions to be asked next
        self.next = []

    def update_score(self, answer, weight, lowbound, highbound):
        """This generic function is in charge of updating the user's current P or W score, taking into account all previous
        answers and their respective weights.
        answer: integer in [0, 1, 2, 3, 4], representing the user's latest answer
        weight: float representing the weight of the last question answered
        lowbound: P/W scale value of the answer corresponding to a 0
        highbound: P/W scale value of the answer corresponding to a 4"""

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
            else:
                self.next = list(adequacy.index[ranking].values)

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