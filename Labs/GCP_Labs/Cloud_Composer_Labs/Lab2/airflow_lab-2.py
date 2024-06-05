from airflow import DAG
from airflow.operators.dummy import DummyOperator
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.providers.google.cloud.sensors.gcs import GCSObjectExistenceSensor
from datetime import datetime, timedelta
from dag_functions import (
    file_operation,
    make_http_request,
    process_file,
    read_and_serialize_return,
    log_file_sensor_output,
)
import logging

AIRFLOW_TASK = "airflow.task"
OUTPUT_PATH = "us-east1-composer-airflow-1c67778d-bucket/data/dag_processed_file.csv"
logger = logging.getLogger(AIRFLOW_TASK)

default_args = {
    'owner': 'Aadit',
    'start_date': datetime(2023, 9, 17),
    'retries': 0,  # Number of retries in case of task failure
    'retry_delay': timedelta(minutes=5),  # Delay before retries
}

dag_1 = DAG(
    'dag_1_parameterize',
    default_args=default_args,
    description='DAG to parameterize file path, process file, and use FileSensor',
    schedule_interval=None,
    catchup=False,
)

read_serialize_task = PythonOperator(
    task_id='read_and_serialize',
    python_callable=read_and_serialize_return,
    op_kwargs={
        'file_path': 'us-east1-composer-airflow-1c67778d-bucket/data/dag_processing_file.csv'
    },
    dag=dag_1,
)

process_task = PythonOperator(
    task_id='process_file',
    python_callable=process_file,
    op_kwargs={
        'output_path': OUTPUT_PATH,
    },
    provide_context=True,
    dag=dag_1,
)

file_sensor_task = GCSObjectExistenceSensor(
    task_id='file_sensor_task',
    bucket='us-east1-composer-airflow-1c67778d-bucket',
    object='data/dag_processed_file.csv',
    poke_interval=10,
    timeout=300,
    dag=dag_1,
    on_success_callback=log_file_sensor_output,
    on_failure_callback=log_file_sensor_output,
)

read_serialize_task >> process_task >> file_sensor_task

dag_2 = DAG(
    'dag_file_and_http',
    default_args=default_args,
    description='DAG for file operations and HTTP request',
    schedule_interval=None,
    catchup=False,
)

file_op_task = PythonOperator(
    task_id='file_operation',
    python_callable=file_operation,
    op_kwargs={'file_path': OUTPUT_PATH},
    dag=dag_2,
)

http_request_task = PythonOperator(
    task_id='http_request',
    python_callable=make_http_request,
    op_kwargs={'url': 'https://jsonplaceholder.typicode.com/todos/1'},
    dag=dag_2,
)

file_op_task >> http_request_task

### DAG 3: Task Dependencies

dag_3 = DAG(
    'dag_3_dependencies',
    default_args=default_args,
    description='DAG to demonstrate task dependencies',
    schedule_interval=None,
    catchup=False,
)

# DummyOperator: Used for grouping and branching logic
start_task = DummyOperator(
    task_id='start_task',
    dag=dag_3,
)

# BashOperator: Runs a simple bash command
bash_task = BashOperator(
    task_id='bash_task',
    bash_command='echo "This is a bash command"',
    dag=dag_3,
)

# PythonOperator: Runs a Python callable
middle_task = PythonOperator(
    task_id='middle_task',
    python_callable=lambda: logger.info("Middle Task"),
    dag=dag_3,
    trigger_rule='all_done',  # Execute regardless of the upstream task's status
)

# DummyOperator: Used for grouping and branching logic
branch_task = DummyOperator(
    task_id='branch_task',
    dag=dag_3,
)

# PythonOperator: Runs a Python callable
end_task = PythonOperator(
    task_id='end_task',
    python_callable=lambda: logger.info("End Task"),
    dag=dag_3,
)

# Set task dependencies
start_task >> [bash_task, branch_task]
bash_task >> middle_task >> end_task
branch_task >> end_task

# If this script is run directly, allow command-line interaction with the DAG
if __name__ == "__main__":
    dag_1.cli()
    dag_2.cli()
    dag_3.cli()
