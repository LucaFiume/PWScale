import numpy as np
import pandas as pd
from Scale import Mapper, Scale, StoreResults


class Tester:
    def __init__(self, max_questions=15, batch=1, load_questions=True, store_results=False):
        # self.user_interface = user_interface #User interface to invoke in order to ask questions
        self.batch = batch  # This number specifies the number of questions to be selected at once
        self.max_questions = max_questions  # Maximum number of questions for P or W
        self.mapper = Mapper()
        # Mapper object translating between the backend scale [-100, 100] and the frontend scale [1,10]
        self.store_results = store_results
        # Boolean indicating whether an excel file containing all results must be created

        if self.store_results:
            self.results = StoreResults(self.mapper)
        else:
            self.results = None

        if load_questions:
            self.qs = pd.ExcelFile('Questions.xlsx', engine='openpyxl')
            self.sa_questions = pd.read_excel(self.qs, 'self_assessment_questions')  # Dataframe with Self-assessment questions
            self.p_questions = pd.read_excel(self.qs, 'P')  # Dataframe with P-related questions
            self.w_questions = pd.read_excel(self.qs, 'W')  # Dataframe with W-related questions

            # Check scales in which these questions work and switch them to the backend scale
            for questions in [self.sa_questions, self.p_questions, self.w_questions]:
                for field in ['Suited for', 'Strongly Disagree', 'Strongly Agree']:
                    scale = self.mapper.which_scale(questions[field])
                    if scale == 1:
                        transformed = self.mapper.front_to_back(questions[field])
                        questions[field] = transformed

        self.P = Scale(self.p_questions, self.sa_questions, batch=batch, battery=int(len(self.sa_questions) / 2),
                       results=self.results)
        self.W = Scale(self.w_questions, self.sa_questions, batch=batch, battery=int(len(self.sa_questions) / 2),
                       results=self.results)

        # Auxiliary variables for the dynamic part of the test
        self.done = False  # Indicates convergence of the dynamic part of the test
        self.dynamic_count = 1  # Number of questions belonging to the dynamic part of the test that have been asked
        self.previousType = 1  # Scale (P or W) to which the previous question is associated (to alternate)

    def receive(self, answers, to_ask, check_convergence=6, is_self_assessment=False, is_video=False):
        """This function interprets the user responses, taking as input:
        answers: List of integers in [0, 1, 2, 3, 4], corresponding to the answers to be analyzed
        to_ask: List of Question IDs to be analyzed
        is_self_assessment: Boolean indicating if these questions correspond to the self_assessment_questions portion
        i: Integer corresponding to the number of questions already asked in the dynamic part of the test
        check_convergence: indicates after which question should convergence be checked"""

        answers_p = []
        answers_w = []
        for j, a in enumerate(answers):
            if 'P' in to_ask[j]:
                answers_p.append(a)
            else:
                answers_w.append(a)

        if not is_video:
            if len(answers_p) > 0 and not self.P.converged:
                self.P.received = answers_p
                self.P.update_score()
                if not is_self_assessment and self.dynamic_count > check_convergence:
                    self.P.check_convergence()

            if len(answers_w) > 0 and not self.W.converged:
                self.W.received = answers_w
                self.W.update_score()
                if not is_self_assessment and self.dynamic_count > check_convergence:
                    self.W.check_convergence()

            if not is_self_assessment:
                self.dynamic_count += 1
        else:
            if len(answers_p) > 0:
                self.P.received = answers_p
                self.P.update_score(continuous=True)
            if len(answers_w) > 0:
                self.W.received = answers_w
                self.W.update_score(continuous=True)

        return self.mapper.back_to_front(self.P.score), self.mapper.back_to_front(self.W.score)

    def self_assessment_emmit(self):
        """This function starts with the self-assessment part of the test, updating the user's P/W scores accordingly"""
        to_ask = []
        for i in range(len(self.sa_questions)):
            qid = self.sa_questions.iloc[i]['Question ID']
            # question = self.sa_questions.iloc[i]['Question']
            scale = self.sa_questions.iloc[i]['P/W']
            weight = self.sa_questions.iloc[i]['Weight']

            # There has to be a coordination between the question database and the class Scale definition.
            # Both have to work with the same scale!
            low_bound = self.sa_questions.iloc[i]['Strongly Disagree']
            high_bound = self.sa_questions.iloc[i]['Strongly Agree']

            if scale == 'P':
                self.P.update_sent(qid, weight, low_bound, high_bound)
            else:
                self.W.update_sent(qid, weight, low_bound, high_bound)

            to_ask.append(qid)

        return to_ask  # List of Question IDs to be asked

    def test_core_emmit(self):
        """Dynamic part of the test. """

        to_ask = []  # List of question IDs to be asked next_question

        scales = [self.P, self.W]
        converged = [self.P.converged, self.W.converged]

        if sum(converged) == 2 or self.dynamic_count > 2 * self.max_questions:
            self.done = True
        else:
            if converged[0] and self.previousType == 1:
                self.previousType = 1
            elif converged[1] and self.previousType == 0:
                self.previousType = 0
            else:
                self.previousType = int(not self.previousType)
            scale = scales[self.previousType]

            next_question = scale.next_question()
            if next_question is not None:
                qid, question, weight, low_bound, high_bound = scale.question_info(next_question)
                scale.update_sent(qid, weight, low_bound, high_bound)
                to_ask.append(qid)

            else:
                self.done = True

        return to_ask, self.done

    def video_emmit(self, video_weight=5):
        """This function emulates what test_core_emmit and self_assessment_emmit do, but instead 'invents' a question ID
        corresponding to the appropriate end videos corresponding to the user's test score. The user will be shown two
        videos corresponding to the upper and lower integer values in the scale. If score is 2.5, videos for 2 and 3
        will be shown.
        For the input:
        video_weight: This shows the weight associated to the user's answer to the videos shown. Note that this answer
        will be treated as any other question of the test."""

        scales = [self.P, self.W]
        to_ask = []
        checkpoints = self.mapper.front_to_back([i for i in range(1, 11)])

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

            qid = title + str(min(other, base)) + '-' + str(max(other, base))
            weight = video_weight
            low_bound = min(other, base)
            high_bound = max(other, base)
            s.update_sent(qid, weight, low_bound, high_bound)
            to_ask.append(qid)

        return to_ask
