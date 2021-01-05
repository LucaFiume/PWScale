from flask import Flask, request, jsonify
from Tester import Tester

app = Flask(__name__)
testers = {}
previousType = {}
questionCount = {}
questionsAsked = {}
finished = {}

"""This script intends to apply Flask for an integration between a Javascript frontend and this Python App. This app
should be used as follows:
1. First, call 'http://.../start?id=...', creating a new test object, taking the user's id as input. The ouput is the question
    IDs of the initial battery of questions.
2. Then, start the dynamic part of the test, given the answers to the static part of the test. This is done by calling
    'http://.../start-dynamic?id=...' from the test frontend. This method takes as input a list of answers, each encoded
    as a whole number from 0 to 4, and returns the question ID of the next question to be asked.
3. For the remaining questions of the dynamic part of the test, the method called with 'http://.../next-dynamic?id=...'
    is used. Here, the frontend inputs the answer of the previous dynamic question, expressed as a list containing a whole
    number ranging from 0 to 4, and returns the question ID of the next question to be asked. 
    The frontend should call this method iteratively until the next question to be asked is None.
4. Once the dynamic part of the video is done, a set of videos associated to the resulting score are displayed. Thus, when
    calling 'http://.../videos?id=...', the corresponding method ouputs the video IDs corresponding to the videos to be shown.
5. Lastly, once the user's answers to the presented videos is received, the method attached to 'http://.../final-report'
    has to be called, taking as input a list of answers, which here can take any value from 0 to 4. Once the user's response
    is inputted, these responses are processed in order to report the final test score."""

@app.route('/start')
def setup():
    user_id = request.args.get('id')
    testers[user_id] = Tester()

    questionsAsked[user_id] = testers[user_id].self_assessment_emmit()
    previousType[user_id] = 'W'
    questionCount[user_id] = 1
    finished[user_id] = False
    return jsonify(questionsAsked[user_id])


@app.route('/start-dynamic')
def start_dynamic():
    user_id = request.args.get('id')
    test = testers[user_id]
    asked = questionsAsked[user_id]
    previous = previousType[user_id]
    count = questionCount[user_id]

    # Still unclear how answers are inputted/encoded here
    answers = request.json
    _, _ = test.receive(answers, asked, isSA=True)
    questionsAsked[user_id], finished[user_id] = test.test_core_emmit(previous, count)
    return jsonify(questionsAsked[user_id])


@app.route('/next-dynamic')
def next_dynamic():
    user_id = request.args.get('id')
    test = testers[user_id]
    asked = questionsAsked[user_id]

    if len(asked) > 0 and not finished[user_id]:
        answers = request.json
        count = questionCount[user_id]

        _, _ = test.receive(answers, asked, count)
        questionCount[user_id] += 1
        previousType[user_id] = asked[-1][0]

    count = questionCount[user_id]
    previous = previousType[user_id]
    questionsAsked[user_id], finished[user_id] = test.test_core_emmit(previous, count)
    return jsonify(questionsAsked[user_id])


@app.route('/videos')
def videos():
    user_id = request.args.get('id')
    test = testers[user_id]
    questionsAsked[user_id] = test.video_emmit()
    return jsonify(questionsAsked[user_id])


@app.route('/final-report')
def report():
    user_id = request.args.get('id')
    test = testers[user_id]
    asked = questionsAsked[user_id]
    answers = request.json
    p_score, w_score = test.receive(answers, asked, isVideo=True)

    del testers[user_id]
    del questionsAsked[user_id]
    del previousType[user_id]
    del questionCount[user_id]
    del finished[user_id]
    return jsonify(p_score), jsonify(w_score)

if __name__ == '__main__':
    app.run()