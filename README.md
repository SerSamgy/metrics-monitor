# Metrics Monitor

A program that monitors the availability of many websites over the network, produces metrics about these and stores 
the metrics into a PostgreSQL database.

## Usage

### Prerequisites

Before you begin, ensure you have met the following requirements:

- You have installed the latest version of `Python 3.11`.
- You have installed the latest version of `Poetry 1.7`.
- You have a running instance of `PostgreSQL` database.

### Steps

1. Clone the repository to your local machine.
2. Navigate to the project directory.
3. Install the required dependencies with `poetry install --without test`. Make sure your Python executable is available in your `PATH` environment variable. 
   
   You could explicitly tell Poetry which Python executable to use before installing the dependencies with `poetry env use <path_to_python_executable>`. So the full command might look like 

    ```shell
    poetry env use /usr/bin/python3.11 && poetry install --without test
    ```

4. Switch to freshly created virtual environment with `poetry shell`.
5. Configure settings for the project. You can do this by creating a `.env` file out of the `.env.prod.default` file and filling in the values. Make sure that value for `POSTGRES_DSN` is correct and leads to your running database instance. Make sure that the rest of settings are correct for your environment.
6. Run the script with the command `python metrics_monitor/main.py <config_file>`, where `<config_file>` is the path to your configuration file.
   
   The configuration file must be a valid JSON file with the following structure:
   
   ```json
    [
        {
            "url": "https://www.example.com/",
            "interval": 10,
            "regexp_pattern": "Example"
        },
        {
            "url": "https://www.another-example.com/",
            "interval": 300,
            "regexp_pattern": null
        }
    ]
   ```

   As a reference, you can use the `websites.json` file in the root of the project.


## Testing

Before running tests, make sure you have installed the dependencies with `poetry install --with test`. Also make sure that you have a running instance of `PostgreSQL` database and prepared a `.env.test` file out of the `.env.test.default` one with correct settings.

To run tests, run the following command in the root of the project

```shell
poetry run pytest
```

To run tests with coverage with report in terminal, run the following command in the root of the project

```shell
poetry run pytest --cov-report term-missing --cov-branch --cov=metrics_monitor/ tests/
```