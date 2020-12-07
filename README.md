# Iterative PWScale Test

This project is focused on developing a backend of the PWScale test website, such that during this test, questions are selected based on previously answered questions. This is intended in order to improve the ability when honing in to a user's particular P or W score.

## Operating Principle

### Attributes of Test Questions
Each P or W question is expected to have the following attributes:
* A Question ID, a string of the form 'P_1' and 'W_1', for questions regarding the P or W scale, respectively ('SA_P_1' or 'SA_W_1' for the initial self-assesment).
* A Question string. This is the actual question.
* A weight k_{P,i} or k_{W,i} indicating the importance of the question,
* A score s_{P,i} or s_{W,i} indicating to which user's P or W score is the question intended,
* A set of bounds [low_{P,i}, high_{P,i}] or [low_{W,i}, high_{W,i}] defining the P or W score associated to each of the question's possible answers. The lower bound corresponds to the answer most to the left, whereas the higher bound corresponds to the answer most to the right. All other answers are linearly interpolated based on these bounds.

### Test Structure

Moreover, the test is structured as follows:
1. Initial Self-Assessment/Calibration: Here, a fixed set of questions from both scales is asked. Based on the user's answers, an initial estimation of the user's P and W scores is obtained.
2. Dynamic Testing without Convergence Checking: Based on the user's latest estimation of P and W scores, the next P or W question is selected. Based on the user's answer, the user's score estimates are updated. These steps are repeated for each question, where questions regarding the P scale are alternated with questions regarding the W scale.
3. Dynamic Testing with Convergence Checking: After a certain number of questions of the previous stage, convergence is checked after every question. The same dynamic selection of the next question holds, but after every answer, it is examined whether certain convergence criteria are fulfilled. If these criteria are fulfilled for a particular scale, (for example if the user's P score has remained constant for the last 5 questions) it is assumed that the user's actual score regarding that scale has been found. After this state, only questions regarding the un-converged scale are asked. The test ends once a maximum of questions has been asked or when all user scores are considered to have converged.

### Estimation of the User's P or W Score

The user's score regarding a scale is computed at any point during the test by taking a weighted average of all previously answered questions regarding that same scale. For instance, for the W scale, if each user answer a_{W,j} for j = 1, ..., n has been stored up to the n-th question of the test, the user's W score at that point of the test is as follows: 

		![equation](https://latex.codecogs.com/gif.latex?W_n&space;=&space;\frac{\sum^{n}_{j}{k_{W,j}&space;\cdot&space;a_{W,j}}}{\sum^{n}_{j}{k_{W,j}}})

### Selection of Next Question
Given that every question has an attribute s_{P,i}, or s_{W,i}, and that at each point of the test, the user's P or W score can be estimated, the next question to be asked is the one whose attribute s_{X,i} is closest to the user's score. This is a minimization over all the questions regarding a particular scale which have not been asked, as is visible in the following equation.

		![equation](https://latex.codecogs.com/gif.latex?Q_W&space;=&space;argmin_{Q_{W,i}}&space;(&space;|s_{W,i}&space;-&space;W_n|))

### Convergence Criteria

Three criteria must be fulfilled in order to assume that a particular score has reached its converged value:
1. The estimated user score must not deviate beyond a tolerance \delta_{score}:

		![equation](https://latex.codecogs.com/gif.latex?\frac{|P_n&space;-&space;P_{n-1}|}{P_{n-1}}&space;<&space;\delta_{score})

2. The user's latest answer regarding a scale must not exceed a deviation \delta_{answer} from the estimated score of that same scale:

		![equation](https://latex.codecogs.com/gif.latex?|a_{W,n}&space;-&space;W_n|&space;<&space;\delta_{answer})

3. The standard deviation of the user's answers in the dynamic part of the test must not deviate more than \delta_{\sigma} from the standard deviation of the user's answers in the initial self-assessment of the test.

		![equation](https://latex.codecogs.com/gif.latex?|\sigma_{SA}&space;-&space;\sigma_{Dymanic}|&space;\delta_{\sigma})

## Project Structure

### FakeWebsite.py

This script is intended to simulate the functions that a JavaScript frontend should call from the other scripts in the project. In short, this script calls the emmitting functions from script Tester.py, thus obtaining the Question IDs to be asked next. Then, these questions are asked (here via a simple printing in the console) and their answers are passed on to the backend by calling function **receive()** from Tester.py. For the initial self-assessment, a fixed set of questions is asked, and backend and frontend interact only once. In contrast, for the rest of the test the frontend is supposed to enter a loop, where for each iteration backend and frontend interact once.

Class Asker is simply intended to print specified prompts in the console, and receive user input. Moreover, class FakeWebsite carries out the aforementioned functions which the website frontend is expected to execute.

### Tester.py

This is the main script defining the backend. Here the dataset containing all questions in the test is loaded, and the functions regarding the emmission to the frontend and the reception of answers from it are defined. Precisely, these functions are implemented within the class Tester. 

On the other hand, calculations regarding the current user estimated scores, the most suitable questions to be asked next, and the convergence checking of each scale score arre implemented in class Scale. This class has two instances: one for the P scale, and another one for the W scale.

Since calculations in the Scale class are carried out with a scale centered around 0, ranging from -100 to 100, a series of functions are defined in function Mapper in order to map values from the backend scale (from -100 to 100) to the frontend scale (from 1 to 4). This class also has a special function used to discern to which scale an array of values is most likely to belong to.

Lastly, class StoreResults is in charge of storing in a pandas dataframe, later saved to an .xlsx file.

### Visualizations.py

This function is merely used to visualize the evolution of a user's scores during the test.



