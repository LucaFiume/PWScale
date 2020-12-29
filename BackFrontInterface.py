from flask import Flask, request, jsonify
from Tester import Tester

app = Flask(__name__)
testers = {}
previousType = {}
questionCount = {}
questionsAsked = {}
finished = {}


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

    answers = request.json
    _, _ = test.receive(answers, asked, isSA=True)
    questionsAsked[user_id], finished[user_id] = test.test_core_emmit(previous, count)
    return questionsAsked[user_id], finished[user_id]

@app.route('/next-dynamic')
def next_dynamic():
    user_id = request.args.get('id')
    test = testers[user_id]
    asked = questionsAsked[user_id]

    if len(asked) > 0:
        answers = request.json
        previousType[user_id] = asked[-1][0]
        previous = previousType[user_id]
        count = questionCount[user_id]

        _, _ = test.receive(answers, asked, count)
        questionCount[user_id] += 1
    questionsAsked[user_id], finished[user_id] = test.test_core_emmit(previous, count)

    return questionsAsked[user_id], finished[user_id]

@app.route('/videos')
def videos():
    user_id = request.args.get('id')
    test = testers[user_id]
    questionsAsked[user_id] = test.video_emmit()
    return questionsAsked[user_id]

@app.route('/final-report')
def report():
    user_id = request.args.get('id')
    test = testers[user_id]
    asked = questionsAsked[user_id]
    answers = request.json
    P_score, W_score = test.receive(answers, asked, isVideo=True)

    del testers[user_id]
    del questionsAsked[user_id]
    del previousType[user_id]
    del questionCount[user_id]
    del finished[user_id]
    return P_score, W_score

if __name__ == '__main__':
    app.run()