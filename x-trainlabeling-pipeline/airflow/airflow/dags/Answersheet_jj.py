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
road = "jj"

# Augment for answersheet(Stationary)
copy_path = f"/mnt/r/seatbelt/{road}_daily_testdata"
weight = 'dataset06.pt'

# Augment for car number plate(Stationary)
highway_dir = f"/mnt/r/seatbelt/highway_send_data/{road}"

def _set_variable(**kwargs):
    today = datetime.date.today()

    today = datetime.date.today()

    days_before = today - datetime.timedelta(days=19)

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

    folder_path = f'/mnt/s/04.seatbelt/01.수집데이터/jukjeon/[R2022-02]죽전휴게소_수집데이터/죽전수집데이터'
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
            if filename.lower().endswith((".jpg", ".jpeg", ".png")) and ("_r_" in filename.lower() or "_l_" in filename.lower()) and "_yolo" not in filename.lower():
                file_list.append((root, filename))
  
    for root, filename in file_list:
        source_file_path = os.path.join(root, filename)
        copy_file_path = os.path.join(copy_dir, filename)
        os.system(f'sudo cp {source_file_path} {copy_file_path}')

    return copy_dir
    
def _make_image_list(detected_folder_path):

    # Get a list of all files in the folder
    image_names = os.listdir(detected_folder_path)

    # Replace '.jpg' with '.txt' for image file names
    image_names = [name.replace('.jpg', '.txt') for name in image_names]

    # Save the list of file names to a text file in the same folder
    with open(os.path.join(detected_folder_path, "image_list.txt"), "w") as file:
        for name in image_names:
            file.write(name + "\n")

def _make_label_list(detected_folder_path):
    
    #label_path
    label_path = os.path.join(detected_folder_path, "labels")
    
    # Get a list of all files in the folder
    label_names = os.listdir(label_path)

    # Save the list of file names to a text file in the same folder
    with open(os.path.join(detected_folder_path, "label_list.txt"), "w") as file:
        for name in label_names:
            file.write(name + "\n")


def _make_empty_file(detected_folder_path):
    file1_path = os.path.join(detected_folder_path, 'label_list.txt')
    file2_path = os.path.join(detected_folder_path, 'image_list.txt')
    label_path = os.path.join(detected_folder_path, 'labels')

    banned_words = ['.csv', '.xlsx', '.db', 'image', 'labels', 'label']  # List of banned words

    # Read file1
    with open(file1_path, 'r') as file1:
        file1_lines = set(line.strip() for line in file1)

    # Read file2
    with open(file2_path, 'r') as file2:
        file2_lines = set(line.strip() for line in file2)

    # Find differences
    differences = file1_lines.symmetric_difference(file2_lines)

    # Remove lines that contain banned words
    differences = [line for line in differences if not any(word in line for word in banned_words)]

    # Create empty text file with differences, if not found
    if differences:
        print("Empty text file detected.")        
        for line in differences:
            # Create empty text file with the line as filename in the label path, if not found and not already exists
            filename_label = os.path.join(label_path, line)
            if not os.path.exists(filename_label):
                open(filename_label, 'w').close()
            else:
                print(f"File '{line}' already exists in the label path.")
    
        print("Total number of different lines: {}".format(len(differences)))
    else:
        print("All files are remining.")

    return label_path

def _check_6_pairs(label_path):
    files = os.listdir(label_path)

    expected_files = ['_r_0', '_r_1', '_r_2', '_l_0', '_l_1', '_l_2']
    missing_files = []

    name_counts = {}
    for file in files:
        road = file.split("_")[0]
        date = file.split("_")[1]
        third_name = file.split("_")[2]
        name_counts[third_name] = name_counts.get(third_name, 0) + 1

    for third_name in name_counts:
        if name_counts[third_name] < 6:
            for expected_file in expected_files:
                missing_file = f"{road}_{date}_{third_name}{expected_file}.txt"
                if missing_file not in files:
                    missing_files.append(missing_file)

    for missing_file in missing_files:
        open(os.path.join(label_path, missing_file), 'w').close()
        print(f"The file '{missing_file}' has been created.")

    if len(missing_files) == 0:
        print("No missing files found.")
            

with DAG(f'answersheet_{road}',
         description="make answersheet",
         tags = ["yolov5"],
         start_date=pendulum.datetime(2022, 1, 1 ,tz="Asia/Seoul"),
         schedule_interval='0 15 * * *',
         catchup=False) as dag:
    
    set_variable = PythonOperator(
        task_id="set_variable",
        python_callable=_set_variable
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
    
    make_image_list = PythonOperator(
        task_id="make_image_list",
        python_callable=_make_image_list,
        op_kwargs={
            'detected_folder_path': "{{ ti.xcom_pull(task_ids='set_variable', key = 'detected_folder_path') }}"
            }
            )

    make_label_list = PythonOperator(
        task_id="make_label_list",
        python_callable=_make_label_list,
        op_kwargs={
            'detected_folder_path': "{{ ti.xcom_pull(task_ids='set_variable', key = 'detected_folder_path') }}"
            }
            )

    make_empty_file = PythonOperator(
        task_id="make_empty_file",
        python_callable=_make_empty_file,
        op_kwargs={
            'detected_folder_path': "{{ ti.xcom_pull(task_ids='set_variable', key = 'detected_folder_path') }}"
            }
            )

    check_6_pairs = PythonOperator(
        task_id="check_6_pairs",
        python_callable=_check_6_pairs,
        op_kwargs={
            'label_path': "{{ ti.xcom_pull(task_ids='make_empty_file') }}"
            }
            )
    
    make_datasheet = BashOperator(
        task_id="make_datasheet",
        bash_command="""
        cd /home/gnt/yolov5
        sudo python3 datasheet.py --source {{ ti.xcom_pull(task_ids='set_variable', key = 'detected_folder_path') }} --name {{ ti.xcom_pull(task_ids='set_variable', key = 'date') }} --weight {{params.weight}}
        """,
        params={
            'weight': weight
            }
            )

    set_variable >> unzip_files >> copy_side_image >> run_object_detection >>[make_image_list, make_label_list] >> make_empty_file >> check_6_pairs >> make_datasheet
    
