# CPS-UAV: Unmanned Aerial Vehicle Testing Competition

## Overview

This is a generator designed for the UAV Testing Competition. The primary approach of this generator involves using a set of randomly placed obstacles as a seed for subsequent GPT-generated test cases. GPT analyzes the drone's flight trajectory within this seed to create challenging test cases. If the test execution of this test case is not determined as a 'hard fail' or 'soft fail,' GPT then analyzes the flight trajectory of this test case and generates a new one, continuing this loop until a suitable test case is found. Once a suitable test case is identified, another set of randomly placed obstacles is used as the seed for generating future test cases, and the method mentioned before is repeated to create test cases.

## Installation and Usage


1. Clone the repository: 
    ```bash
    git clone https://github.com/Trusted-AI-in-System-Test/UAV-Testing-Competition.git    
	```

2. Navigate to the snippets folder:
    ```bash
    cd UAV-Testing-Competition/snippets
    ```

3. Create a Docker Image:
	```bash
    sudo docker build -t [YOUR_IMAGE_NAME] .
    ```

4. Setting .env file:
	```bash
    cd ..
	vim .env
    ```
	```plaintext
	# .env file

	# Add your ChatGPT API key here
	chatGPT_api_key=YOUR_API_KEY
	
	#Change your ChatGPT model
	chatGPT_model=GPT_MODEL

5. Run the Docker container:
	```bash
    sudo docker run --env-file .env -dit [YOUR_IMAGE_NAME]

	sudo docker exec -it [CONTAINER_ID] bash
    ```
	
6. Run the generator:
	```bash
    python3 cli.py generate [PATH_TO_MISSION_YAML] [BUDGET]
    ```

## Author

- Taohong Zhu
  - Email: taohong.zhu@postgrad.manchester.ac.uk
  - Affiliation: The University of Manchester

- Youcheng Sun
  - Email: youcheng.sun@manchester.ac.uk
  - Affiliation: The University of Manchester

- Suzanne Embury
  - Email: suzanne.m.embury@manchester.ac.uk
  - Affiliation: The University of Manchester

- William Newton
  - Email: william.newton@student.manchester.ac.uk
  - Affiliation: The University of Manchester


