import numpy as np
import pandas as pd
from Scale import Mapper, Scale, StoreResults

class Tester:
    def __init__(self, numQs=15, batch=1, loadQs=True, bounds=[-100, 100], storeResults=False):
        # self.user_interface = user_interface #User interface to invoke in order to ask questions
        self.batch = batch #This number specifies the number of questions to be selected at once
        self.numQs = numQs #Maximum number of questions for P or W
        self.mapper = Mapper(backBounds=bounds) #Mapper object translating between the backend scale [-100, 100] and the frontend scale [1,4]
        self.storeResults = storeResults #Boolean indicating whether an excel file containing all results must be created

        if self.storeResults:
            self.results = StoreResults(self.mapper)
        else:
            self.results = None

        if loadQs:
            self.qs = pd.ExcelFile('Questions.xlsx', engine='openpyxl')
            self.SA_questions = pd.read_excel(self.qs, 'SA') #Dataframe with Self-assessment questions
            self.P_questions = pd.read_excel(self.qs, 'P') #Dataframe with P-related questions
            self.W_questions = pd.read_excel(self.qs, 'W') #Dataframe with W-related questions

            #Check scales in which these questions work and switch them to the backend scale
            for questions in [self.SA_questions, self.P_questions, self.W_questions]:
                for field in ['Suited for', 'Strongly Disagree', 'Strongly Agree']:
                    scale = self.mapper.which_scale(questions[field])
                    if scale == 1:
                        transformed = self.mapper.front_to_back(questions[field])
                        questions[field] = transformed

        self.P = Scale(self.P_questions, self.SA_questions, batch=batch, bounds=bounds, battery=len(self.SA_questions), results=self.results)
        self.W = Scale(self.W_questions, self.SA_questions, batch=batch, bounds=bounds, battery=len(self.SA_questions), results=self.results)
        self.done = False

    def receive(self, answers, toAsk, i=0, check_convergence=10, isSA=False, isVideo=False):
        """This function interprets the user responses, taking as input:
        answers: List of integers in [0, 1, 2, 3, 4], correspoding to the answers to be analyzed
        toAsk: List of Question IDs to be analyzed
        isSA: Boolean indicating if these questions correspond to the SA portion
        i: Integer corresponding to the number of questions already asked in the dynamic part of the test
        check_convergence: indicates after which question should convergence be checked"""

        answersP = []
        answersW = []
        for j, a in enumerate(answers):
            if 'P' in toAsk[j]:
                answersP.append(a)
            else:
                answersW.append(a)

        if not(isVideo):
            if len(answersP) > 0 and not(self.P.converged):
                self.P.received = answersP
                self.P.update_score()
                if not(isSA) and i > check_convergence:
                    self.P.check_convergence()

            if len(answersW) > 0 and not(self.W.converged):
                self.W.received = answersW
                self.W.update_score()
                if not(isSA) and i > check_convergence:
                    self.W.check_convergence()
        else:
            if len(answersP) > 0:
                self.P.received = answersP
                self.P.update_score(continuous=True)
            if len(answersW) > 0:
                self.W.received = answersW
                self.W.update_score(continuous=True)

        if not(isVideo):
            return self.P.score, self.W.score
        else:
            return self.mapper.back_to_front(self.P.score), self.mapper.back_to_front(self.W.score)

    def self_assessment_emmit(self):
        """This function starts with the self-assessment part of the test, updating the user's P/W scores accordingly"""
        toAsk = []
        for i in range(len(self.SA_questions)):
            QID = self.SA_questions.iloc[i]['Question ID']
            # question = self.SA_questions.iloc[i]['Question']
            scale = self.SA_questions.iloc[i]['P/W']
            weight = self.SA_questions.iloc[i]['Weight']

            #There has to be a coordination between the question database and the class Scale definition. Both have to work with the same scale!
            lowbound = self.SA_questions.iloc[i]['Strongly Disagree']
            highbound = self.SA_questions.iloc[i]['Strongly Agree']

            if scale == 'P':
                self.P.update_sent(QID, weight, lowbound, highbound)
            else:
                self.W.update_sent(QID, weight, lowbound, highbound)

            toAsk.append(QID)

        return toAsk #List of Question IDs to be asked

    def test_core_emmit(self, previousType, i=1):
        """Dynamic part of the test. check_convergence indicates after which question should convergence be checked
        previousType is a string indicating whether the previously asked question was P or W scale. Can be 'P' or 'W'"""

        toAsk = [] #List of question IDs to be asked next

        if previousType == 'W':
            previousType = 1
        else:
            previousType = 0

        scales = [self.P, self.W]
        converged = [self.P.converged, self.W.converged]

        if sum(converged) == 2 or i > 2 * self.numQs:
            self.done = True
        else:
            if converged[0] and previousType == 1:
                scale = scales[1]
            elif converged[1] and previousType == 0:
                scale = scales[0]
            else:
                scale = scales[int(not(previousType))]

            next = scale.next_question()
            if next is not None:
                QID, question, weight, lowbound, highbound = scale.question_info(next)
                scale.update_sent(QID, weight, lowbound, highbound)
                toAsk.append(QID)
            else:
                self.done = True

        return toAsk, self.done

    def video_emmit(self, videoWeight=5):
        """This function emulates what test_core_emmit and self_assessment_emmit do, but instead 'invents' a question ID
        corresponding to the appropriate end videos corresponding to the user's test score. The user will be shown two videos
        corresponding to the upper and lower integer values in the scale. If score is 2.5, videos for 2 and 3 will be shown.
        For the input:
        videoWeight: This shows the weight associated to the user's answer to the videos shown. Note that this answer
        will be treated as any other question of the test."""

        scales = [self.P, self.W]
        toAsk = []
        checkpoints = self.mapper.front_to_back([i for i in range(1, 5)])

        for i, s in enumerate(scales):
            base = np.argmin(abs(checkpoints - s.score))

            if s.score > checkpoints[base]:
                other = checkpoints[base + 1]
            elif s.score < checkpoints[base]:
                other = checkpoints[base - 1]
            else:
                if base == len(checkpoints):
                    other = checkpoints[base - 1]
                else:
                    other = checkpoints[base + 1]

            base = self.mapper.back_to_front(checkpoints[base])
            other = self.mapper.back_to_front(other)

            if i == 0:
                title = 'Video_P_'
            else:
                title = 'Video_W'

            QID = title + str(min(other, base)) + '-' + str(max(other, base))
            weight = videoWeight
            lowbound = min(other, base)
            highbound = max(other, base)
            s.update_sent(QID, weight, lowbound, highbound)
            toAsk.append(QID)

        return toAsk


