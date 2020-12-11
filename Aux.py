import pyautogui
import pyperclip
import numpy as np
import gspread
from time import sleep
import pandas as pd
from datetime import datetime, timedelta


def typeText(input: str):
    for singleChar in input:
        if singleChar not in "@=;\\*\"'!%&<>/_čćšđžČĆŠĐŽ":
            pyautogui.typewrite(singleChar)
        else:
            pyperclip.copy(singleChar)
            pyautogui.hotkey("ctrlleft", "v")


def identify_outliers(data, m=1.5):
    data = np.array(data)
    d = np.abs(data - np.median(data))
    mdev = np.median(d)
    s = d / (mdev if mdev else 1.)
    return data[s > m]

# def identify_outliers(sr, iq_range=0.4):
#     sr = pd.Series(sr)
#     print(sr)
#     pcnt = (1 - iq_range) / 2
#     qlow, median, qhigh = sr.dropna().quantile([pcnt, 0.50, 1 - pcnt])
#     iqr = qhigh - qlow
#     return sr[(sr - median).abs() <= iqr]


def saveToGSheets(data: dict, course: str, assignment: str):
    print("Saving to GSheets!")
    gc = gspread.service_account()
    sh = gc.open(f"{course}2020")

    try:
        sheet = sh.worksheet(f'Z{assignment.split(" ")[-1]}')
        sh.del_worksheet(sheet)
    except Exception as e:
        pass

    sheet = sh.add_worksheet(
        title=f'Z{assignment.split(" ")[-1]}',
        rows=f'{len(data)+10}',
        cols="20"
    )

    sheet.update(
        "A1", '=ARRAYFORMULA(INDIRECT(ADDRESS(1,1,1,1,"Studenti")&":"&ADDRESS(COUNTA(Studenti!A:A),3)))', raw=False)
    sleep(1)
    sheet.update("D1", [["in", "out", "Σ"]])

    for num, row in progressBar(sheet.get_all_values(), prefix = 'Storing grades in GSheet:', suffix = 'grades stored.', length = 20):
    # for num, row in enumerate(sheet.get_all_values(), start=1):
        fullname = ' '.join(row[:2])
        if fullname in data:
            student = data[fullname]
            sheet.update(f'D{num+1}',
                         [[student['in'], student['out'], student['sum']]])
            sleep(1) # Google provides a limit of write requests per user per 100 seconds

def progressBar(iterable, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)

    Modified from: https://stackoverflow.com/a/34325723
    """
    total = len(iterable)
    startTime = datetime.now()
    # Progress Bar Printing Function
    def printProgressBar (iteration, eta = ''):
        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        filledLength = int(length * iteration // total)
        bar = fill * filledLength + '-' * (length - filledLength)
        print(f'\r{prefix} |{bar}| {percent:5}% {suffix} {eta}', end = printEnd)
    # Initial Call
    printProgressBar(0)
    # Update Progress Bar
    for i, item in enumerate(iterable):
        yield i, item
        timePassed = datetime.now() - startTime
        eta = startTime + timedelta(seconds=(timePassed.seconds / (i+1) * total))
        eta = f"ETA: {eta.strftime('%H:%M:%S')}"
        printProgressBar(i + 1, eta=eta)
    # Print New Line on Complete
    print()
