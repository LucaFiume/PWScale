import numpy as np
import pandas as pd

class Tester:
    def __init__(self, numQs=15, batch=1, loadQs=True, bounds=[-100, 100], storeResults=True):
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
            self.qs = pd.ExcelFile('Questions.xlsx')
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



class Scale:
    """This simple class is made to store the information regarding each of the two scales in an efficient way, no need
    to repeat the same code for each scale"""
    def __init__(self, questions, SA, batch=1, bounds=[-100, 100], battery=10, results=None):
        #Dataframe of questions relative to the scale
        self.questions = questions
        # Dataframe of questions relative to the SA part of the test
        self.SA_questions = SA
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
        #Fulfillment of criteria
        self.criteria = [0, 0, 0]
        #ID of questions corresponding to this scale sent to the front end, awaiting answer
        self.sent = []
        #Weights of questions corresponding to this scale sent to the front end, awaiting answer
        self.sentWeights = []
        # Lowbounds of questions corresponding to this scale sent to the front end, awaiting answer
        self.sentLow = []
        # Highbounds of questions corresponding to this scale sent to the front end, awaiting answer
        self.sentHigh = []
        # received is a list of received answers still to be applied to update the final score. Same order as in sent
        self.received = []
        #This invokes the class StoreResults, in charge of writing up the results
        self.results = results

    def update_score(self, continuous=False, base=10):
        """This generic function is in charge of updating the user's current P or W score, taking into account all previous
        answers and their respective weights.
        answer: integer in [0, 1, 2, 3, 4], representing the user's latest answer.
        if continuous is True, answer is an integer between 0 and 4
        weight: float representing the weight of the last question answered
        lowbound: Scale value of the answer corresponding to a 0
        highbound: Scale value of the answer corresponding to a 4"""

        for i, answer in enumerate(self.received):
            lowbound = self.sentLow[i]
            highbound = self.sentHigh[i]
            weight = self.sentWeights[i]
            if continuous:
                answer = (answer / base) * highbound + lowbound
            else:
                answer = np.linspace(lowbound, highbound, 5)[answer]
            self.answers.append(answer)
            self.weights.append(weight)

            result = 0
            for j, ans in enumerate(self.answers):
                result += ans * self.weights[j]
            result = result / sum(self.weights)
            self.score = result
            self.history.append(result)

            if self.results is not None:
                sent = self.sent[i]

                if 'SA' in sent:
                    question = self.SA_questions.loc[self.SA_questions['Question ID'] == sent, ['Question']].values[0][0]
                elif 'Video' in sent:
                    question = sent
                else:
                    question = self.questions.loc[self.questions['Question ID'] == sent, ['Question']].values[0][0]

                if 'P' in sent:
                    type = 'P'
                else:
                    type = 'Q'

                self.results.newLine(sent, question, lowbound, highbound, type, answer, self.score)

        #Reset all communication buffers to be empty
        self.sent = []
        self.sentWeights = []
        self.sentLow = []
        self.sentHigh = []
        self.received = []


    def next_question(self):
        """This function finds the question most suited for the current score"""
        if len(self.next) == 0:
            mask = self.questions['Question ID'].isin(self.answered)
            mask = [not(m) for m in mask]
            adequacy = self.questions.loc[mask]['Suited for']
            ranking = np.argsort(np.abs(adequacy.values - self.score))
            QIDs = self.questions.loc[mask]['Question ID']

            if len(ranking) > self.batch:
                self.next = list(QIDs.iloc[ranking[0:self.batch]].values)
            elif len(ranking) > 0:
                self.next = list(QIDs.iloc[ranking].values)
            else:
                # print('ERROR: No questions remain.')
                self.converged = True
                self.next = [None]

        next = self.next[0] #Immediately next question
        self.next.pop(0)
        return next #this is a question ID

    def question_info(self, QID):
        """This function returns the question info associated with the question ID in QID"""
        mask = self.questions['Question ID'] == QID
        question = self.questions.loc[mask, ['Question']].values[0][0]
        weight = self.questions.loc[mask, ['Weight']].values[0][0]
        lowbound = self.questions.loc[mask, ['Strongly Disagree']].values[0][0]
        highbound = self.questions.loc[mask, ['Strongly Agree']].values[0][0]
        self.answered.append(QID)
        return QID, question, weight, lowbound, highbound

    def check_convergence(self, tol=100, deltaMu=50, deltaSigma=50):
        """Here, the three existing convergence criteria are checked at the same time, with the three tolerance parameters
        set as an input. If all three criteria are satisfied, it is said that the score has converged."""

        score_converged = self.check_score_convergence(tol)
        delta_mean_converged = self.check_delta_mean(deltaMu)
        delta_std_converged = self.check_delta_std(deltaSigma)
        if score_converged and delta_mean_converged and delta_std_converged:
            self.converged = True

        for i, crit in enumerate([score_converged, delta_mean_converged, delta_std_converged]):
            if crit and self.criteria[i] == 0:
                self.criteria[i] = len(self.history)

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

            if dev < tolerance:
                score_converged = True
        return score_converged

    def check_delta_mean(self, delta=0.5):
        """This function checks the deviation existing between the score of the user's last answered question and the user's
        score before such question. If the deviation is above the input float delta, it is said that the user's delta is
        that of a converged test."""

        delta_mean_converged = False
        if len(self.history) > 1:
            dev = abs(self.answers[-1] - self.history[-2])
            if dev < delta:
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
            if dev < delta:
                delta_std_converged = True
        return delta_std_converged

    def update_sent(self, QID, weight, lowbound, highbound):
        """This function simply updates all the 'sent' attributes of the class"""
        self.sent.append(QID)
        self.sentWeights.append(weight)
        self.sentLow.append(lowbound)
        self.sentHigh.append(highbound)


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
        try:
            y = x * self.f2b['Slope'] + self.f2b['Add']
        except:
            y = np.array(x) * self.f2b['Slope'] + self.f2b['Add']

        try:
            y = max(y, self.backBounds[0])
            y = min(y, self.backBounds[1])
        except:
            for i, e in enumerate(y):
                y[i] = max(min(e, self.backBounds[1]), self.backBounds[0])

        return y

    def back_to_front(self, x):
        """Here, values in x, expressed in the backend scale, are converted to the frontend scale."""
        x = round(x, 5)
        try:
            #x is an iterable
            if max(x) > self.backBounds[1] or min(x) < self.backBounds[0]:
                print("ERROR: Values to be converted to the frontend scale are beyond the backend scale's bounds")

            y = x * self.b2f['Slope'] + self.b2f['Add']
            for i in range(len(y)):
                closest = np.argmin(abs(self.frontValues - y[i]))
                y[i] = self.frontValues[closest]
        except:
            # x is not an iterable
            if x > self.backBounds[1] or x < self.backBounds[0]:
                print("ERROR: Values to be converted to the frontend scale are beyond the backend scale's bounds")

            y = x * self.b2f['Slope'] + self.b2f['Add']
            closest = np.argmin(abs(self.frontValues - y))
            y = self.frontValues[closest]

        return y

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
        except:
            if x < np.max([self.backBounds[0], self.frontBounds[0]]):
                left_says = left_widest
            else:
                left_says = None

            if x > np.min([self.backBounds[1], self.frontBounds[1]]):
                right_says = right_widest
            else:
                right_says = None

            if left_says is None:
                if right_says is None:
                    print('ERROR: Values to be detected are ambiguous')
                    scale = None
                else:
                    scale = right_says
            else:
                if right_says is not None:
                    print('ERROR: Values to be detected are ambiguous')
                    scale = None
                else:
                    scale = left_says

        return scale


class StoreResults:
    def __init__(self, mapper):
        """This class takes care of storing results in a dataframe appropriately"""
        self.results = pd.DataFrame(
            columns=['Question Number', 'QID', 'Question', 'Type', 'Lower Bound', 'Higher Bound', 'Answer', 'P Score after',
                     'W Score after'])
        self.mapper = mapper

    def newLine(self, QID, question, lowbound, highbound, type, answer, score):
        if type == 'P':
            scoreP = score
            if len(self.results) > 0:
                scoreW = self.results.iloc[-1]['W Score after']
                scoreW = self.mapper.front_to_back(scoreW)
            else:
                scoreW = 0
        else:
            scoreW = score
            if len(self.results) > 0:
                scoreP = self.results.iloc[-1]['P Score after']
                scoreP = self.mapper.front_to_back(scoreP)
            else:
                scoreP = 0

        self.results = self.results.append(
            {'Question Number': len(self.results) + 1, 'QID': QID, 'Question': question, 'Type': type, 'Lower Bound': lowbound,
             'Higher Bound': highbound, 'Answer': self.mapper.back_to_front(answer),
             'P Score after': self.mapper.back_to_front(scoreP),
             'W Score after': self.mapper.back_to_front(scoreW)}, ignore_index=True)

    def save(self, name, dir='./Results/PWScale Results '):
        self.results.to_excel(dir + name + '.xlsx', index=False, float_format="%.3f")