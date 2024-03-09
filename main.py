#!/usr/bin/python3

import zipfile
import json
import csv
import pathlib

PASSWORD_ITEMS = []
PASSWORD_DATA_FILE = '/export.data'
BASE_FILE_NAME = None
PARENT_DIRECTORY = None
OUTPUT_DIRECTORY = '/output'
TMP_DIRECTORY = OUTPUT_DIRECTORY + '/tmp'


def extract_1password_file():
    with zipfile.ZipFile(PARENT_DIRECTORY + '/' + BASE_FILE_NAME + '.1pux', 'r') as zip_ref:
        zip_ref.extractall(PARENT_DIRECTORY + TMP_DIRECTORY)


def convert_to_keychain():
    f = open(PARENT_DIRECTORY + TMP_DIRECTORY + PASSWORD_DATA_FILE)
    data = json.load(f)
    f.close()
    for i in data['accounts'][0]['vaults'][0]['items']:
        title = i['overview']['title']
        url = i['overview']['url']
        username = None
        password = None
        if len(i['details']['loginFields']) > 0:
            for j in i['details']['loginFields']:
                if 'name' in j and 'value' in j:
                    if j['name'] == 'username':
                        username = j['value']
                    elif j['name'] == 'password':
                        password = j['value']
        item = dict({'Title': title, 'URL': url, 'Username': username, 'Password': password})
        PASSWORD_ITEMS.append(item)


def export_as_csv():
    fields = ['Title', 'URL', 'Username', 'Password', 'Notes', 'OTPAuth']
    with open(PARENT_DIRECTORY + '/' + OUTPUT_DIRECTORY + '/' + BASE_FILE_NAME + ".csv", 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fields)
        writer.writeheader()
        writer.writerows(PASSWORD_ITEMS)


if __name__ == '__main__':
    input_file_name = input("Enter 1Password exported file name along with path: ")
    if input_file_name is None or input_file_name == '':
        print("Please enter a valid file name")
        exit(-1)

    if not pathlib.Path(input_file_name).is_file():
        print("File does not exists or its not a file. Please check and try again")
        exit(-2)

    PARENT_DIRECTORY = str(pathlib.Path(input_file_name).parent.resolve(True))
    BASE_FILE_NAME = str(pathlib.Path(input_file_name).stem)
    extract_1password_file()
    convert_to_keychain()
    export_as_csv()
