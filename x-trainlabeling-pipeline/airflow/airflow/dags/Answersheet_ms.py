from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.sensors.filesystem import FileSensor
from airflow.utils.task_group import TaskGroup

import datetime
import pendulum
import pandas as pd
import zipfile
import os
import base64
import requests
import re

# Augment for answersheet(Volatile)
road = "ms"

# Augment for answersheet(Stationary)
copy_path = f"/mnt/r/seatbelt/{road}_daily_testdata"
weight = 'hovlane_221101_b16_e5002weights.pt'

# Augment for car number plate(Stationary)
highway_dir = f"/mnt/r/seatbelt/highway_send_data/{road}"

def _set_variable(**kwargs):
    today = datetime.date.today()

    today = datetime.date.today()

    days_before = today - datetime.timedelta(days=23)

    year = days_before.year

    month = days_before.month

    day = days_before.day

    # Check if the month is less than 10
    if month < 10:
        # Pad the month with a leading zero
        month = "0" + str(month)

    # Check if the date is less than 10
    if day < 10:
        # Pad the date with a leading zero
        day = "0" + str(day)

    date = str(year)[2:4] + str(month) + str(day)

    folder_path = f'/mnt/h/01.수집데이터/01._마성터널_데이터/{year}-{month}'
    folder_name = road + "_" + date
    project_path = os.path.join(copy_path, "detect")
    detected_folder_path = os.path.join(project_path, folder_name)
    month = date[:4]

    kwargs['ti'].xcom_push(key='date', value=date)
    kwargs['ti'].xcom_push(key='folder_path', value=folder_path)
    kwargs['ti'].xcom_push(key='folder_name', value=folder_name)
    kwargs['ti'].xcom_push(key='project_path', value=project_path)
    kwargs['ti'].xcom_push(key='detected_folder_path', value=detected_folder_path)
    kwargs['ti'].xcom_push(key='month', value=month)

def _unzip_files(folder_path, date):
    
    zip_file_path = os.path.join(folder_path, date + '.zip')
    
    with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
        extract_path = os.path.join(folder_path, date)
        zip_ref.extractall(extract_path)

    return extract_path

def _copy_side_image(extract_path, date, copy_path):

    copy_dir = os.path.join(copy_path, date)
    os.makedirs(copy_dir, exist_ok=True)

    file_list = []

    for root, dirs, files in os.walk(extract_path):
        for filename in files:
            if filename.lower().endswith((".jpg", ".jpeg", ".png")) and "side" in filename.lower() and "_yolo" not in filename.lower():
                file_list.append((root, filename))
  
    for root, filename in file_list:
        source_file_path = os.path.join(root, filename)
        copy_file_path = os.path.join(copy_dir, filename)
        os.system(f'sudo cp {source_file_path} {copy_file_path}')

    return copy_dir

with DAG(f'answersheet_{road}',
         description="make answersheet",
         tags = ["yolov5"],
         start_date=pendulum.datetime(2022, 1, 1 ,tz="Asia/Seoul"),
         schedule_interval='0 21 * * *',
         catchup=False) as dag:

    set_variable = PythonOperator(
        task_id = 'set_variable',
        python_callable = _set_variable
        )
    
    unzip_files = PythonOperator(
        task_id="unzip_files",
        python_callable=_unzip_files,
        op_kwargs={'folder_path' :"{{ti.xcom_pull(task_ids='set_variable', key = 'folder_path')}}",
                   'date': "{{ti.xcom_pull(task_ids='set_variable', key = 'date')}}"
                   }
                   )
    
    copy_side_image = PythonOperator(
        task_id="copy_side_image",
        python_callable=_copy_side_image,
        op_kwargs={'extract_path': "{{ ti.xcom_pull(task_ids='unzip_files') }}",
                    'date': "{{ti.xcom_pull(task_ids='set_variable', key = 'date')}}",
                    'copy_path': copy_path
                    }
                    )
    
    run_object_detection = BashOperator(
        task_id="run_object_detection",
        bash_command="""
        cd /home/gnt/yolov5
        sudo python3 detect.py --weights {{ params.weight }} --source "{{ ti.xcom_pull(task_ids='copy_side_image') }}" --project {{ ti.xcom_pull(task_ids='set_variable', key = 'project_path') }} --save-txt --save-conf --conf 0.55  --name {{ ti.xcom_pull(task_ids='set_variable', key = 'folder_name') }} --save-txt --save-conf --conf 0.55
        """,
        params={
            'weight': weight
            }
            )
    
    make_datasheet = BashOperator(
        task_id="make_datasheet",
        bash_command="""
        cd /home/gnt/yolov5
        sudo python3 ms_datasheet.py --date {{ ti.xcom_pull(task_ids='set_variable', key = 'date') }}
        """
        )
    
    set_variable >> unzip_files >> copy_side_image >> run_object_detection >> make_datasheet
