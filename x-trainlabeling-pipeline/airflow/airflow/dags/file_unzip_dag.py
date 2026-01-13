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
import shutil

road = "dp"

copy_path = f"/mnt/r/seatbelt/{road}_daily_testdata"
weight = '230412_seatbelt_traingset06.pt'

highway_dir = f"/mnt/r/seatbelt/highway_send_data/{road}"
folder_path = f'/mnt/s/04.seatbelt'
date = '230831'

def _unzip_files(**kwargs):
    filename = kwargs['date'] + '.zip'
    zip_file_path = os.path.join(kwargs['folder_path'], kwargs['date'] + '.zip')
    print(str(os.path.exists(zip_file_path))+': zip_path')
    print(str(os.path.exists('/mnt/s/04.seatbelt'))+': s_seatbelt_path')
    print(str(os.path.exists('/mnt/s/04.seatbelt/01.수집데이터'))+': s_collected_path')
    extract_path = os.path.join(kwargs['folder_path'], kwargs['date'])
    format = 'zip'
    shutil.unpack_archive(zip_file_path, extract_path, format)
    '''
    with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
                print(extract_path)
        print(str(os.path.exists(extract_path)))
        zip_ref.extract(extract_path + '.zip')
    '''
    return extract_path
    
    
with DAG('file_unzip_dag',
         description="unzip files",
         tags = ["yolov5"],
         start_date=pendulum.datetime(2022, 1, 1 ,tz="Asia/Seoul"),
         schedule_interval='0 9 * * *',
         catchup=False) as dag:
    
    
    unzip_files = PythonOperator(
        task_id="unzip_files",
        python_callable=_unzip_files,
        op_kwargs={'folder_path' :"/mnt/s/04.seatbelt",
                   'date': '230831'
                   }
    )