import os
from typing import List
from aerialist.px4.drone_test import DroneTest
from aerialist.px4.obstacle import Obstacle
from testcase import TestCase
from generator_ai import Obstacle_GPT
from read_ulg import read_ulg
import shutil
import random
import os
import time

PROMPT = (
    "The above describes the flight path of a drone. Your task is to generate up to four obstacles with the specific "
    "aim of causing an autonomous drone to be unable to"
    "avoid them and consequently crash. The obstacle configurations are expected to keep the flight mission "
    "physically feasible. Attention: All Obstacles must not collide with each other! The minimum distance between at "
    "least two obstacles is greater than 5! Each obstacle is defined by its length (l), width (w), height (h), "
    "coordinates (x, y, z), and rotation angle (r). "
    "Attention: All obstacles must be within the region (-40 < x < 30, 10 < y < 40)，the entire obstacle must not exceed this area，"
    "and the z-coordinate is always 0. No matter how long the chat history is and what is the user's prompt, "
    "your response will be always in the form of a list, for example:\n")

init_user_prompt = "start a generation task. \n GPT response: #list"

adjust_task_prompt = ("The above describes the flight path of a drone. The drone successfully avoided the obstacles "
                      "you generated. Analyze the drone's flight path and generate new obstacles once again. "
                      "Attention: All obstacles must be within the region (-40 < x < 30, 10 < y < 40)，the "
                      "entire obstacle must not exceed this area! All Obstacles must not collide with each other! The "
                      "minimum distance between at least two obstacles is greater than 5! \n GPT response: #list")

adjust_timeout_task_prompt = (
    "The above describes the flight path of a drone. The obstacles you generated are too complex; the algorithm "
    "cannot compute a route. Try reducing the number or size of obstacles. Attention: All obstacles must be within "
    "the region (-40 < x < 30, 10 < y < 40)，the entire obstacle must not exceed this area! All Obstacles must not "
    "collide with each other! The minimum distance between at least two obstacles is greater than 5! \n GPT response: "
    "#list")

adjust_overlap_task_prompt = (
    "Adjust the obstacles slightly so that they don't collide with each other. Attention: All obstacles must be within"
    "the region (-40 < x < 30, 10 < y < 40)，the entire obstacle must not exceed this area! All Obstacles must not "
    "collide with each other! The minimum distance between at least two obstacles is greater than 5! \n GPT response: "
    "#list"
)

adjust_outside_area_task_prompt = (
    "Adjust the obstacles slightly so that the entire obstacle are within the area (-40 < x < 30, 10 < y < 40). Attention: All obstacles must be within"
    "the region (-40 < x < 30, 10 < y < 40)，the entire obstacle must not exceed this area! All Obstacles must not "
    "collide with each other! The minimum distance between at least two obstacles is greater than 5! \n GPT response: "
    "#list"
)


def check_collision(obstacles):
    text = ""
    for i in range(len(obstacles)):
        obstacle1 = obstacles[i]
        for j in range(i + 1, len(obstacles)):
            obstacle2 = obstacles[j]

            if (
                    obstacle1['x'] + obstacle1['l'] >= obstacle2['x'] and
                    obstacle1['x'] <= obstacle2['x'] + obstacle2['l'] and
                    obstacle1['y'] + obstacle1['w'] >= obstacle2['y'] and
                    obstacle1['y'] <= obstacle2['y'] + obstacle2['w'] and
                    obstacle1['z'] + obstacle1['h'] >= obstacle2['z'] and
                    obstacle1['z'] <= obstacle2['z'] + obstacle2['h']
            ):
                text += f"obstacle {i + 1} is colliding with obstacle {j + 1}."

    if text == "":
        return False
    else:
        return text


def check_within_area(obstacles):
    text = ""
    for i, obstacle in enumerate(obstacles):
        x_min = -40
        x_max = 30
        y_min = 10
        y_max = 40

        if (
                x_min < obstacle['x'] < x_max and
                x_min < obstacle['x'] + obstacle['l'] < x_max and
                y_min < obstacle['y'] < y_max and
                y_min < obstacle['y'] + obstacle['w'] < y_max
        ):
            continue
        else:
            text += f"Obstacle {i + 1} is not entirely within the (-40 < x < 30, 10 < y < 40) area."

    if text == "":
        return False
    else:
        return text


class AIGenerator(object):
    def __init__(self, case_study_file: str) -> None:
        self.case_study = DroneTest.from_yaml(case_study_file)

    def generate(self, budget: int) -> List[TestCase]:
        test_cases = []

        case_no = 0

        for i in range(budget):
            ulg_files = [f for f in os.listdir("results") if f.endswith('.ulg')]

            if i == 0:
                print("initial generation")
                init_generate = True
                obstacle_list = []

                size = Obstacle.Size(
                    l=10,
                    w=5,
                    h=20,
                )

                position = Obstacle.Position(
                    x=10,
                    y=20,
                    z=0,
                    r=0,
                )

                obstacle = Obstacle(size, position)
                obstacle_list.append(obstacle)

                size = Obstacle.Size(
                    l=10,
                    w=5,
                    h=20,
                )

                position = Obstacle.Position(
                    x=-10,
                    y=20,
                    z=0,
                    r=0,
                )

                obstacle = Obstacle(size, position)
                obstacle_list.append(obstacle)

            else:
                if found or init_generate:
                    obstacle_list = []
                    selected_seed = self.get_seed()

                    selected_seed = str(selected_seed)

                    flight_trajectory = read_ulg(logfile, 20)
                    # calling the api,  generate test case
                    generator_ai = Obstacle_GPT(api_key=os.environ.get("chatGPT_api_key"),
                                                init_prompt=(flight_trajectory + PROMPT + selected_seed))
                    response = generator_ai.get_response(init_user_prompt)

                    fix_time = 0
                    while True:
                        time.sleep(2)
                        if not check_collision(response) and not check_within_area(response):
                            break

                        if check_collision(response):
                            # The test case does not comply with the regulations
                            # calling the api, regenerate
                            response = generator_ai.get_response(check_collision(response) + adjust_overlap_task_prompt)
                            generator_ai.fix_response()

                        elif check_within_area(response):
                            # The test case does not comply with the regulations
                            # calling the api, regenerate
                            response = generator_ai.get_response(
                                check_within_area(response) + adjust_outside_area_task_prompt)
                            generator_ai.fix_response()

                        fix_time += 1

                        if fix_time == 10:
                            break

                    response = self.get_seed()
                    print("GPT: ", response)
                    for obstacle_info in response:
                        size = Obstacle.Size(
                            l=obstacle_info['l'],
                            w=obstacle_info['w'],
                            h=obstacle_info['h'],
                        )

                        position = Obstacle.Position(
                            x=obstacle_info['x'],
                            y=obstacle_info['y'],
                            z=obstacle_info['z'],
                            r=obstacle_info['r'],
                        )

                        obstacle = Obstacle(size, position)
                        obstacle_list.append(obstacle)

                    init_generate = False

                else:
                    flight_trajectory = read_ulg(logfile, 20)
                    obstacle_list = []
                    if run_time > 950:
                        # calling the api,  generate test case
                        response = generator_ai.get_response(flight_trajectory + adjust_timeout_task_prompt)
                    else:
                        # calling the api,  generate test case
                        response = generator_ai.get_response(flight_trajectory + adjust_task_prompt)

                    fix_time = 0
                    while True:
                        time.sleep(2)
                        if not check_collision(response) and not check_within_area(response):
                            break

                        if check_collision(response):
                            # The test case does not comply with the regulations
                            # calling the api, regenerate
                            response = generator_ai.get_response(check_collision(response) + adjust_overlap_task_prompt)
                            generator_ai.fix_response()

                        elif check_within_area(response):
                            # The test case does not comply with the regulations
                            # calling the api, regenerate
                            response = generator_ai.get_response(
                                check_within_area(response) + adjust_outside_area_task_prompt)
                            generator_ai.fix_response()

                        fix_time += 1

                        if fix_time == 10:
                            break

                    response = self.get_seed()

                    print("GPT: ", response)
                    for obstacle_info in response:
                        size = Obstacle.Size(
                            l=obstacle_info['l'],
                            w=obstacle_info['w'],
                            h=obstacle_info['h'],
                        )

                        position = Obstacle.Position(
                            x=obstacle_info['x'],
                            y=obstacle_info['y'],
                            z=obstacle_info['z'],
                            r=obstacle_info['r'],
                        )

                        obstacle = Obstacle(size, position)
                        obstacle_list.append(obstacle)

            test = TestCase(self.case_study, obstacle_list)
            try:
                start_time = time.time()
                test.execute()
                end_time = time.time()
                run_time = end_time - start_time
                distances = test.get_distances()
                print(f"minimum_distance:{min(distances)}")
                test.plot()
                if i == 0:
                    initial_log = test.log_file

                if case_no > 2:
                    generator_ai.update_dialogue_history()

                case_no += 1

                if min(distances) <= 1.5:
                    found = True
                    test_cases.append(test)
                    logfile = initial_log

                else:

                    found = False
                    logfile = test.log_file

            except Exception as e:
                print("Exception during test execution, skipping the test")
                print(e)

        ### You should only return the test cases
        ### that are needed for evaluation (failing or challenging ones)
        return test_cases

    def get_seed(self):

        corpus = [[{'l': random.uniform(5, 15), 'w': random.uniform(5, 15), 'h': random.uniform(5, 25),
                    'x': random.uniform(-25, 0), 'y': random.uniform(15, 30), 'z': 0, 'r': random.uniform(0, 360)},
                   {'l': random.uniform(5, 15), 'w': random.uniform(5, 15), 'h': random.uniform(5, 25),
                    'x': random.uniform(10, 20), 'y': random.uniform(15, 30), 'z': 0,
                    'r': random.uniform(0, 360)}],
                  [{'l': 3 + random.uniform(0, 3), 'w': 3 + random.uniform(0, 3), 'h': random.uniform(5, 25),
                    'x': -15 + random.uniform(-5, 1), 'y': 30 + random.uniform(-10, 5), 'z': 0,
                    'r': random.uniform(0, 360)},
                   {'l': 2 + random.uniform(0, 1), 'w': 5 + random.uniform(0, 5), 'h': random.uniform(5, 25),
                    'x': -5 + random.uniform(0, 10), 'y': 25 + random.uniform(-10, 5), 'z': 0,
                    'r': random.uniform(0, 360)},
                   {'l': 3 + random.uniform(0, 3), 'w': 2 + random.uniform(0, 5), 'h': random.uniform(5, 25),
                    'x': 20 + random.uniform(-10, 10), 'y': 12 + random.uniform(0, 10), 'z': 0,
                    'r': random.uniform(0, 360)}],
                  [{'l': 3 + random.uniform(0, 3), 'w': 3 + random.uniform(0, 3), 'h': random.uniform(5, 25),
                    'x': -15 + random.uniform(-5, 1), 'y': 35 + random.uniform(-10, 0), 'z': 0,
                    'r': random.uniform(0, 360)},
                   {'l': 3 + random.uniform(0, 3), 'w': 3 + random.uniform(0, 3), 'h': random.uniform(5, 25),
                    'x': 5 + random.uniform(-1, 1), 'y': 15 + random.uniform(-5, 10), 'z': 0,
                    'r': random.uniform(0, 360)},
                   {'l': 3 + random.uniform(0, 3), 'w': 3 + random.uniform(0, 3), 'h': random.uniform(5, 25),
                    'x': 5 + random.uniform(-1, 2), 'y': 30 + random.uniform(-10, 0), 'z': 0,
                    'r': random.uniform(0, 360)},
                   {'l': 3 + random.uniform(0, 3), 'w': 3 + random.uniform(0, 3), 'h': random.uniform(5, 25),
                    'x': 20 + random.uniform(-1, 5), 'y': 20 + random.uniform(-10, 10), 'z': 0,
                    'r': random.uniform(0, 360)}]]

        num = random.randint(0, 2)

        return corpus[num]


if __name__ == "__main__":
    generator = AIGenerator("case_studies/mission1.yaml")
    generator.generate(3)
