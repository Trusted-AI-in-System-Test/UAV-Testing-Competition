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


class AIGenerator(object):
    def __init__(self, case_study_file: str) -> None:
        self.case_study = DroneTest.from_yaml(case_study_file)
        self.corpus = [[{'l': 10, 'w': 5, 'h': 20, 'x': 10, 'y': 20, 'z': 0, 'r': 0},
                        {'l': 10, 'w': 5, 'h': 20, 'x': -10, 'y': 20, 'z': 0, 'r': 0}],
                       [{'l': 20, 'w': 20, 'h': 40, 'x': 30, 'y': 20, 'z': 0, 'r': 0},
                        {'l': 20, 'w': 20, 'h': 40, 'x': -30, 'y': 20, 'z': 0, 'r': 0}]]

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
                    selected_seed = self.corpus.pop(0)
                    self.corpus = self.add_seed(self.corpus)
                    selected_seed = str(selected_seed)

                    ulg_files.sort(key=lambda x: os.path.getmtime(os.path.join("results", x)))
                    logfile = "results/" + ulg_files[0]
                    flight_trajectory = read_ulg(logfile, 20)

                    generator_ai = Obstacle_GPT(api_key=os.environ.get("chatGPT_api_key"),
                                                init_prompt=(flight_trajectory + PROMPT + selected_seed))
                    response = generator_ai.get_response(init_user_prompt)

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

                    ulg_files = [f for f in os.listdir("results") if f.endswith('.ulg')]
                    ulg_files.sort(key=lambda x: os.path.getmtime(os.path.join("results", x)))
                    logfile = "results/" + ulg_files[-1]
                    flight_trajectory = read_ulg(logfile, 20)
                    obstacle_list = []
                    if run_time > 950:
                        response = generator_ai.get_response(flight_trajectory + adjust_timeout_task_prompt)
                    else:
                        response = generator_ai.get_response(flight_trajectory + adjust_task_prompt)
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

                if case_no > 2:
                    generator_ai.update_dialogue_history()

                case_no += 1

                if min(distances) <= 1.5:
                    found = True
                    test_cases.append(test)

                else:

                    found = False

            except Exception as e:
                print("Exception during test execution, skipping the test")
                print(e)

        ### You should only return the test cases
        ### that are needed for evaluation (failing or challenging ones)
        return test_cases

    def add_seed(self, corpus):

        seed = [{'l': random.uniform(5, 30), 'w': random.uniform(5, 30), 'h': random.uniform(5, 40),
                 'x': random.uniform(-40, 30), 'y': random.uniform(10, 40), 'z': 0, 'r': random.uniform(0, 360)},
                {'l': random.uniform(5, 30), 'w': random.uniform(5, 30), 'h': random.uniform(5, 40),
                 'x': random.uniform(-40, 30), 'y': random.uniform(10, 40), 'z': 0, 'r': random.uniform(0, 360)}]

        corpus.append(seed)

        return corpus


if __name__ == "__main__":
    generator = AIGenerator("case_studies/mission1.yaml")
    generator.generate(3)
