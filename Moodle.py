from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.select import Select
import pyautogui
import pyperclip
from time import sleep
from numpy import std, mean
import numpy as np
import re
import random
import argparse
import datetime
import os
import shutil
from credentials import creds
from Aux import identify_outliers, typeText, saveToGSheets, progressBar
import Classcraft

COURSES = {
    "VAS": {
        "link": "https://elf.foi.hr/course/view.php?id=133",
        "fullname": "Višeagentni sustavi"
    },
    "DP": {
        "link": "https://elf.foi.hr/course/view.php?id=164",
        "fullname": "Deklarativno programiranje"
    },
    "TBP": {
        "link": "https://elf.foi.hr/course/view.php?id=135",
        "fullname": "Teorija baza podataka"
    }
}

FILENAME = []

DEFECTIVETHRESHOLD = 10

DRIVER = None


class Submission():
    """Class describing an instance of submitted work."""

    def __init__(self, student: str, address: str = None, markOut: int = None, markIn: int = None):
        self.address = address
        self.markIn = markIn
        self.markInOld = None
        self.markOut = markOut
        if markOut:
            if markIn:
                self.markSum = markIn + markOut
            else:
                self.markSum = markOut
        else:
            self.markSum = None
        self.student = student
        self.marks = {}
        self.givenMarks = {}
        self.markMean = 0
        self.markStdDev = 0
        self.defective = False
        self.slacker = False
        self.course = None
        self.courseAcr = None
        self.assignment = None

    def calculateForOutliers(self):
        try:
            # self.markMean = mean([v['mark']
            #                       for v in self.marks.values() if v['mark'] is not None])
            self.markStdDev = std([v['mark']
                                   for v in self.marks.values() if v['mark'] is not None])
        except:
            pass

        if self.markStdDev > DEFECTIVETHRESHOLD:
            self.defective = True

    def calculateForSlackers(self):
        if self.marks and len([k for k, v in self.givenMarks.items() if v['mark'] is None]) > len(self.givenMarks) * 0.5:
            # print([k for k, v in self.givenMarks.items() if v['mark'] is None])
            self.slacker = True
            self.markIn = int(self.markIn * 0.7)
            try:
                self.markSum = self.markIn + self.markOut
            except Exception as e:
                # print(f"Have not calculated slack penalty for {self.student}.")
                self.markSum = self.markIn
                # pass

    def addAssessment(self, student: str, mark: int, link: str, given: bool = False):
        if given:
            self.givenMarks[link] = {'student': student, 'mark': mark}
        else:
            self.marks[link] = {'student': student, 'mark': mark}

    def prepareDataForSheets(self):
        return {
            'in': self.markIn,
            'out': self.markOut,
            'sum': self.markSum,
            'received': self.marks
        }

    def __str__(self) -> str:
        if not self.marks:
            return f"{self.student} did not submit their assignment."

        if not [k for k, v in self.marks.items() if v['mark'] is not None]:
            return f"{self.student} submitted their assignment, but was not yet graded."

        if not self.markSum:
            assessmentsReceived = [
                f"{v['student']} ({v['mark']})" for v in self.marks.values() if v['mark'] is not None]
            assessmentsGiven = [
                f"{v['student']} ({v['mark']})" for v in self.givenMarks.values() if v['mark'] is not None]
            return f"{self.student}\n\twas graded by: {', '.join(assessmentsReceived) if assessmentsReceived else 'nobody'}\n\tgave grades to: {', '.join(assessmentsGiven) if assessmentsGiven else 'nobody'}"

        assessmentsReceived = [
            f"{v['student']} ({v['mark']})" for v in self.marks.values() if v['mark'] is not None]
        assessmentsGiven = [
            f"{v['student']} ({v['mark']})" for v in self.givenMarks.values() if v['mark'] is not None]
        return f"{self.student} (received: {f'{self.markInOld} -> ' if self.markInOld else ''}{self.markIn}{'!' if self.slacker else ''}, given: {self.markOut}, sum: {self.markSum})\n\t{'may have been incorrectly' if self.defective else 'was'} graded by: {', '.join(assessmentsReceived) if assessmentsReceived else 'nobody'}\n\tgave grades to: {', '.join(assessmentsGiven) if assessmentsGiven else 'nobody'}"


def doMoodleLogin(usr: str, password: str):
    try:
        DRIVER.find_element_by_xpath(
            '//*[@id="page-wrapper"]/nav/ul[2]/li[3]/div/span/a').click()
        DRIVER.find_element_by_id("username").send_keys(
            usr,
            Keys.TAB,
            password,
            Keys.ENTER)
    except Exception as e:
        pass


def getSubmissionBasic():
    rows = DRIVER.find_elements_by_xpath(
        '//table[contains(@class, "grading-report")]/tbody/tr'
    )

    course = DRIVER.find_element_by_xpath(
        '//*[@id="page-header"]//h1'
    ).text
    courseAcr = DRIVER.find_element_by_xpath(
        f'//*[@id="page-navbar"]//a[@title="{course}"]'
    ).text
    assignment = DRIVER.find_element_by_xpath(
        '//*[@id="region-main"]//h2[1]'
    ).text

    submissions = []
    total = len(rows)

    for _, row in progressBar(rows, prefix = 'Getting info:', suffix = 'info on submissions collected.', length = 20):
        try:
            student = row.find_element_by_xpath(
                './/td[contains(@class,"participant")]//span'
            ).text

            submissions.append(Submission(student=student))

            submissions[-1].course = course
            submissions[-1].courseAcr = courseAcr
            submissions[-1].assignment = assignment
        except:
            pass

        try:
            received = row.find_element_by_xpath(
                './td[contains(@class, "receivedgrade")][./div[@class="assessmentdetails"]]'
            )

            try:
                mark = int(received.find_element_by_xpath(
                    './/span[@class="grade"]'
                ).text)
            except Exception as e:
                mark = None

            student = received.find_element_by_xpath(
                './/span[@class="fullname"]'
            ).text

            link = received.find_element_by_xpath(
                './/a[@class="grade"]'
            ).get_attribute("href")

            submissions[-1].addAssessment(student, mark, link)
        except Exception as e:
            pass

        try:
            given = row.find_element_by_xpath(
                './td[contains(@class, "givengrade")][./div[@class="assessmentdetails"]]'
            )

            try:
                mark = int(given.find_element_by_xpath(
                    './/span[@class="grade"]'
                ).text)
            except Exception as e:
                mark = None

            student = given.find_element_by_xpath(
                './/span[@class="fullname"]'
            ).text

            link = given.find_element_by_xpath(
                './/a[@class="grade"]'
            ).get_attribute("href")

            submissions[-1].addAssessment(student, mark, link, given=True)
        except Exception as e:
            pass

        try:
            link = row.find_element_by_xpath(
                './/td[contains(@class,"submission")]/a'
            ).get_attribute("href")
            submissions[-1].address = link
        except Exception as e:
            continue

        try:
            mark = row.find_element_by_xpath(
                './/td[contains(@class, "submissiongrade")]'
            )
            try:
                markIn = int(mark.text)
            except Exception as e:
                markIn = int(mark.find_element_by_xpath('./ins').text)
                markInOld = int(mark.find_element_by_xpath('./del').text)
                submissions[-1].markInOld = markInOld
            submissions[-1].markIn = markIn
            submissions[-1].markSum = markIn
        except Exception as e:
            # markIn = None
            # markOut = None
            continue

        try:
            markOut = int(row.find_element_by_xpath(
                './/td[contains(@class, "gradinggrade")]'
            ).text)
            submissions[-1].markOut = markOut
            submissions[-1].markSum += markOut
        except Exception as e:
            # markOut = None
            pass

    return submissions


def downloadFiles(sub: Submission):
    DRIVER.get(sub.address)

    link = DRIVER.find_element_by_xpath(
    '//div[@class="submission-full"]//div[@class="attachments"]//a'
    )

    ActionChains(DRIVER).context_click(link).perform()

    downloadedName = f'{sub.courseAcr}TempDl'

    pyautogui.press('k', interval=0.5)
    typeText(downloadedName)
    pyautogui.press('enter', interval=0.5)

    # shutil.move(f"~/Downloads/{sub.courseAcr} - {sub.assignment} - {sub.student}.*", dst)

    # downloadedPath = os.path.join("~", 'Downloads', f"{downloadedName}.zip")
    downloadedPath = os.path.join("/home", "bogdan", 'Downloads', f"{downloadedName}.zip")

    sleep(3)

    try:
        shutil.unpack_archive(
            downloadedPath,
            f'{sub.courseAcr} {sub.assignment}/{sub.student}'
        )
    except Exception as e:
        print(f'{sub.student}\'s submission not downloaded.')

    os.remove(downloadedPath)

    DRIVER.back()


def getSubmissionFiles(submissions: list):
    # if not os.path.isdir(f'{submissions[0].courseAcr}{submissions[0].assignment}'
    os.makedirs(f'{submissions[0].courseAcr} {submissions[0].assignment}', exist_ok=True)

    for _, sub in progressBar(submissions, prefix = 'Downloading files:', suffix = 'files downloaded.', length = 20):

        if not sub.address:
            continue

        downloadFiles(sub)


def repairDefective(outliers: list):
    for _, k in progressBar(outliers, prefix = 'Repairing outliers:', suffix = 'outlying assessments\' weights set to 0.', length = 20):
        DRIVER.get(k)
        try:
            Select(DRIVER.find_element_by_id("id_weight")).select_by_value("0")
            DRIVER.find_element_by_id("id_feedbackreviewer_editoreditable").send_keys(
            "Težinska vrijednost ocjene postavljena je na 0 zato što dodijeljena ocjena previše odskače od ostalih procjena iste zadaće."
            )
        except Exception as e:
            pass
        DRIVER.find_element_by_id("id_save").click()


def identifyDefective(subs: list, repair: bool = False):
    for sub in subs:
        sub.calculateForOutliers()

    f = open(FILENAME[0], "a")

    print(f"\nIdentifying assignments with potentially defective assessment.")
    f.write(f"\n\n\nAssignments with potentially defective assessment ({len([s for s in subs if s.defective])}):\n")

    defective = []

    for sub in [s for s in subs if s.defective]:
        f.write(f"\n{sub}")

        outliers = identify_outliers([v['mark']
                                      for v in sub.marks.values() if v['mark'] is not None])

        outliers = {k: v for k, v in sub.marks.items() if v['mark'] in outliers}

        for k, v in outliers.items():
            f.write(f"\n\t\tSuspect: {v['student']}: {k}")
            defective.append(k)

    if repair:
        repairDefective(defective)

        DRIVER.find_element_by_id("id_submit").click()

    f.close()


def suggestSample(subs: list):
    f = open(FILENAME[0], "a")

    # print(f"\nRandom check suggestion:")
    f.write(f"\n\n\nRandom sample:\n")
    suggestion = random.sample(
        [sub.student for sub in subs if sub.marks],
        int(len(subs) * 0.15)
    )
    # print("\n".join(suggestion))
    f.write("\n".join(suggestion))

    f.close()


def getTopMarks(subs: list) -> list:
    subs = [sub for sub in subs if sub.marks]
    f = open(FILENAME[0], "a")

    print(f"\nCalculating top 10%.")
    f.write(f"\n\n\nTop 10%:\n")

    top = subs[:int(len(subs) * 0.1 if len(subs) * 0.1 > 1 else 1)]
    f.write("\n".join([sub.__str__() for sub in top]))

    f.close()

    return top


def getLowestMarks(subs: list) -> list:
    subs = [sub for sub in subs if sub.marks]
    f = open(FILENAME[0], "a")

    print(f"\nCalculating bottom 10%.")
    f.write(f"\n\n\nBottom 10%:\n")

    btm = subs[int(len(subs) * 0.9):]
    f.write("\n".join([sub.__str__() for sub in btm]))

    f.close()

    return btm


def getWorkshopLink(courseLink: str):
    DRIVER.get(courseLink)

    try:
        doMoodleLogin(creds['user'], creds['password'])
    except Exception as e:
        print(e)
        pass

    return DRIVER.find_element_by_xpath(
        '//a[text()="Laboratorijske vježbe"]/../../..//li[contains(@class, "activity workshop")][last()]//a'
    ).get_attribute("href")


def showPlenty():

    e = DRIVER.find_element_by_xpath(
        '//select[@class="custom-select singleselect"][@name="perpage"]'
    )

    try:
        Select(e).select_by_value("300")
    except Exception as e:
        pass


def saveSubmissionsInfo(submissions: list, initial: bool = True):
    courseAcr = submissions[0].courseAcr
    assignment = submissions[0].assignment

    print(f"\n{'-'*13}\nReport for: {courseAcr} - {assignment} - N: {len(submissions)}\n{'-'*13}")

    if not len(FILENAME):
        FILENAME.append(f"{courseAcr} - {assignment} - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}.txt")

    if initial:
        f = open(FILENAME[0], "w")
        f.write(f"{courseAcr} - {assignment} - N: {len(submissions)}\n\n\n")
    else:
        f = open(FILENAME[0], "a")
        f.write(f"\n\n\n{'-'*13}\nRevised assessments\n\n\n")

    for sub in submissions:
        f.write(f"\n{sub}")
    f.close()


def penaliseSlackers(slackers: dict):
    for k, v in slackers.items():
        DRIVER.get(k)
        try:
            Select(DRIVER.find_element_by_id("id_gradeover")).select_by_value(f"{v['mark']}")
            DRIVER.find_element_by_id("id_feedbackauthor_editoreditable").send_keys(
                "Primijenjena penalizacija (nova ocjena = izvorna ocjena * 0.7) zato što nije napravljena procjena za više od dva rada."
            )
        except Exception as e:
            pass
        DRIVER.find_element_by_id("id_save").click()


def identifySlackers(subs: list, repair: bool = False):
    for sub in subs:
        sub.calculateForSlackers()

    f = open(FILENAME[0], "a")

    print(f"\nIdentifying slackers.")
    f.write(f"\n\n\nStudents who submitted their assignments, and received grades, but assessed none:\n")

    slackers = {s.address: {'mark': s.markIn, 'student': s.student} for s in subs if s.slacker}

    f.write('\n'.join([s['student'] for s in slackers.values()]))

    if repair:
        penaliseSlackers(slackers)

    f.close()


def scoreClasscraft(submissions: list, feedback: dict):
    f = open(FILENAME[0], "a")
    f.write(f"\n\n\n{'-'*13}\nClasscraft Input\n\n\n")
    f.write(f"\n{feedback}\n")
    f.close()

    Classcraft.DRIVER = DRIVER
    Classcraft.main(
        course=submissions[0].course,
        feedback=feedback
    )


def main(link: str, identify: bool = False, suggest: bool = False, scoring: bool = False, classcraft: bool = False, download: bool = False, gSheets: bool=False, repair: bool=False, slackers: bool=False):
    print(f"{'#'*13}\nNow performing on {link}\n{'#'*13}")

    DRIVER.get(link)

    try:
        doMoodleLogin(creds['user'], creds['password'])
    except Exception as e:
        print(e)
        pass

    showPlenty()

    submissions = getSubmissionBasic()

    saveSubmissionsInfo(submissions)

    if download:
        getSubmissionFiles(submissions)

    if identify:
        # identify those submissions where there are outliers, and repair if identified
        identifyDefective(submissions, repair=repair)

    if repair:
        submissions = []
        # get the new state of submissions
        submissions = getSubmissionBasic()

        saveSubmissionsInfo(submissions, initial=False)

    if slackers:
        identifySlackers(submissions, repair=repair)

    if suggest:
        suggestSample(submissions)

    if scoring:
        forScoring = sorted([s for s in submissions if s.markIn is not None], key=lambda x: x.markIn, reverse=True)

        top = getTopMarks(forScoring)
        btm = getLowestMarks(forScoring)

        if classcraft:
            feedback = {
                sub.student: {
                    'positive': True,
                    'behaviour': 1
                } for sub in top
            }
            feedback.update({
                sub.student: {
                    'positive': False,
                    'behaviour': 3
                } for sub in btm
            })
            scoreClasscraft(submissions, feedback)

    if gSheets:
        saveToGSheets(
            {
                sub.student: sub.prepareDataForSheets() for sub in submissions
            },
            course=submissions[0].courseAcr,
            assignment=submissions[0].assignment)

    FILENAME = []
    submissions = []


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="A script for opening ELF in a browser and collecting and providing feedback on workshops."
    )
    parser.add_argument("-c", "--courses", type=str, nargs="*",
                        default=["VAS", "TBP", "DP"], help="A list of acronym(s) of the course(s)")
    parser.add_argument("-w", "--workshops", type=str, nargs="*",
                        default=None, help="A list of link(s) to specific workshop(s)")
    parser.add_argument("--select", dest="select", action="store_true",
                        help="A random subset of N * 0.15 assignments will be selected")
    parser.add_argument("--dl", dest="download", action="store_true",
                        help="Download assignment attachments")
    parser.add_argument("--analyse-all", dest="analyse", action="store_true",
                        help="Set --outliers and --slackers")
    parser.add_argument("--outliers", dest="outliers", action="store_true",
                        help="Outlying assessments will be identified")
    parser.add_argument("--slackers", dest="slackers", action="store_true",
                        help="Students who received grades, but gave no grades, will be identified; requires --outliers")
    parser.add_argument("--repair", dest="repair", action="store_true",
                        help="Repair outlying assessments by giving them weight=0 and slackers by giving them received grade * 0.7; requires --outliers or --slackers")
    parser.add_argument("--scores-full", dest="scoresFull", action="store_true",
                        help="Set --scores and --ccraft and --gsheets")
    parser.add_argument("--scores", dest="scores", action="store_true",
                        help="Top N * 0.1 and bottom N * 0.1 assignments will be given")
    parser.add_argument("--ccraft", dest="ccraft", action="store_true",
                        help="Top and bottom scores will be acknowledged in Classcraft")
    parser.add_argument("--gsheets", dest="gSheets", action="store_true",
                        help="Store grades to GSheets")
    parser.add_argument("--gui", dest="gui", action="store_true",
                        help="Show GUI. Cancels --dl if set")
    parser.set_defaults(
        select=False,
        download=False,
        outliers=False,
        slackers=False,
        repair=False,
        scores=False,
        ccraft=False,
        gSheets=False,
        gui=False,
        analyse=False,
        scoresFull=False,
    )
    args = parser.parse_args()

    if args.analyse:
        args.outliers = True
        args.slackers = True

    if args.scoresFull:
        args.scores = True
        args.ccraft = True
        args.gSheets = True

    opt = Options()
    # opt.binary_location = "/opt/vivaldi/vivaldi"
    if not args.gui:
        opt.add_argument("--headless")
        args.download = False
    opt.add_argument("--incognito")
    DRIVER = webdriver.Chrome(options=opt, executable_path="./chromedriver")

    if args.workshops:
        for w in args.workshops:
            main(w,
                 suggest=args.select,
                 download=args.download,
                 identify=args.outliers,
                 slackers=args.slackers,
                 repair=args.repair,
                 scoring=args.scores,
                 classcraft=args.ccraft,
                 gSheets=args.gSheets)
    else:
        for c in args.courses:
            link = getWorkshopLink(COURSES[c]["link"])
            main(link,
                 suggest=args.select,
                 download=args.download,
                 identify=args.outliers,
                 slackers=args.slackers,
                 repair=args.repair,
                 scoring=args.scores,
                 classcraft=args.ccraft,
                 gSheets=args.gSheets)

    DRIVER.quit()
