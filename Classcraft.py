from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.action_chains import ActionChains
import pyautogui
import pyperclip
import argparse
import time
from credentials import ccreds
import datetime
from Aux import progressBar


DRIVER = None


def sleep(sec: int):
    time.sleep(sec)


def clickIt(element: WebElement):
    ActionChains(DRIVER).move_to_element(element).click(element).perform()


def findElementXpath(xpath: str, single: bool = True) -> WebElement:
    sleep(1)
    success = False
    start = datetime.datetime.now()
    now = 0
    while not success and now <= 13:
        try:
            if single:
                element = DRIVER.find_element_by_xpath(
                    xpath
                )
            else:
                element = DRIVER.find_elements_by_xpath(
                    xpath
                )
            success = True
            return element
        except:
            now = datetime.datetime.now() - start
            now = now.seconds
            sleep(now / 13 if now / 13 > 0.1 else 0.1)

    raise Exception(f"Timed out finding: {xpath}")


def doClasscraftLogin(usr: str, password: str):
    e = findElementXpath('//div[@class="Login__toggle-button-wrap"]/button')
    clickIt(e)
    sleep(1)
    DRIVER.find_element_by_id("input:username").send_keys(
        usr,
        Keys.TAB,
        password,
        Keys.ENTER)


def skipWalkthrough():
    print("Waiting for walkthrough.")
    e = findElementXpath('//div[@title="Stop Walk-thru"]')
    clickIt(e)


def openCourse(course: str):
    e = findElementXpath(
        f'//button[@class="classInfo"]/div[contains(text(),"{course}")]')
    sleep(1)
    try:
        e.location_once_scrolled_into_view()
    except:
        pass
    clickIt(e)

    sleep(1)
    e = findElementXpath(
        '//div[contains(@class, "PlayerList scroll")]/div[@class="PlayerListItem"][2]')
    clickIt(e)

    try:
        skipWalkthrough()
        pass
    except Exception as e:
        print(e)
        pass


def openListOfStudents():
    sleep(2)

    e = findElementXpath(
        '//button[contains(@class, "TippyButton sidebarItem-general-users")]/*[@class="Icon general-users"]')
    clickIt(e)

    e = findElementXpath('//div[@class="headerCenter"]/a[1]')
    clickIt(e)


def openClassList():
    sleep(2)

    e = findElementXpath(
        '//button[contains(@class, "TippyButton sidebarItem-general-users")]/*[@class="Icon general-users"]')
    clickIt(e)

    e = findElementXpath('//div[@class="headerCenter"]/a[3]')
    clickIt(e)


def filterStudent(student: str):
    e = findElementXpath('//input[@class="FilterInput searchField small"]')
    e.clear()
    e.send_keys(student)


def giveFeedback(student: str, positive: bool = True, behav: int = 1) -> None:
    # print(f"{student} was {'not ' if not positive else ''}good, they deserve {'reward' if positive else 'penalty'}: {behav}")

    filterStudent(student)

    e = findElementXpath(
        '//div[contains(@class, "PlayerList scroll")]/div[contains(@class, "PlayerListItem")]')
    clickIt(e)

    sleep(1)
    if positive:
        sleep(1)
        try:
            clickIt(DRIVER.find_element_by_id("addPositiveBtn"))
        except Exception as e:
            print(f"{student} cannot be rewarded.")
            return
    else:
        # return # uncomment this to avoid giving negative feedback
        sleep(1)
        try:
            clickIt(DRIVER.find_element_by_id("addNegativeBtn"))
        except Exception as e:
            print(f"{student} cannot be penalised.")
            return

    sleep(1)
    e = findElementXpath(f'//div[@class="BehaviorCardsList"]/div[{behav}]')
    clickIt(e)

    if not positive:
        sleep(1)
        e = findElementXpath('//div[@class="playerCard dealLaterBtn"]')
        clickIt(e)
        sleep(1)


def acknowledgeBehaviour(student: str, positive: bool = True, behav: int = 1) -> None:
    openListOfStudents()

    giveFeedback(student, positive, behav)


def acknowledgeBehaviours(students: dict) -> None:
    openListOfStudents()

    for _, (k, v) in progressBar(students.items(), prefix = 'Applying behaviours:', suffix = 'behaviours applied.', length = 20):
        giveFeedback(k, v['positive'], v['behaviour'])


def readQuestFeedback(students: dict) -> list:
    feedback = students
    e = findElementXpath(
        '//table[@class="ObjectiveProgressTableWrapper"]/tbody/tr', single=False)

    for _, aFeedback in progressBar(e, prefix = 'Getting assignment status:', suffix = 'assignment statuses collected.', length = 20):
        student = aFeedback.find_element_by_xpath('./td[1]/span').text

        try:
            state = aFeedback.find_element_by_xpath(
                './/td/div').get_attribute("class")

            if "dot late" in state:
                feedback[student] = {'positive': False, 'behaviour': 2}
            elif "dot timely" in state or "dot early" in state:
                feedback[student] = {'positive': True, 'behaviour': 2}
        except:
            continue

    # print(feedback)

    return feedback


def giveQuestFeedback(questName: str = None, behavs: bool = False):
    openListOfStudents()

    students = {}

    e = findElementXpath('//div[contains(@class, "PlayerList scroll")]')
    name = e.find_element_by_xpath('./div')
    while True:
        students[name.text] = {'positive': False, 'behaviour': 1}
        try:
            name.location_once_scrolled_into_view
        except Exception as e:
            pass
        try:
            name = name.find_element_by_xpath(
                './following-sibling::div[contains(@class,"PlayerListItem")]')
        except Exception as e:
            break

    # print(students)

    e = findElementXpath(
        '//button[contains(@class, "TippyButton sidebarItem-general-quest")]/*[@class="Icon general-quest"]')
    clickIt(e)

    e = findElementXpath('//div[@class="headerLeftTop"]//span')
    course = e.text

    if questName:
        try:
            e = findElementXpath(
                f'//div[@class="title"][contains(text(),"{questName}")]/../..')
            clickIt(e)
        except Exception as e:
            print(f"Quest name was given ({questName}), but no such quest found.")
            return
    else:
        e = findElementXpath('//div[@class="QuestNode"]')
        clickIt(e)

        e = findElementXpath(
            '//div[@class="headerLeftBottom"]//button[@class="TippyDropDown breadcrumb clickable"]')
        clickIt(e)

        if "VIŠEAGENTNI SUSTAVI" in course:
            e = findElementXpath(
                '//div[contains(@class, "TippyDropDownTooltip")]/a[starts-with(text(),"Q")][last()]')
            clickIt(e)
        else:
            e = findElementXpath(
                '//div[contains(@class, "TippyDropDownTooltip")]/a[last()]')
            clickIt(e)

    e = findElementXpath('//button[@class="TippyDropDown breadcrumb clickable"]/span')
    questName = e.text

    e = findElementXpath(
        '//div[@class="ObjectiveNode"]')
    clickIt(e)

    e = findElementXpath(
        '//div[@class="ObjectiveListWrapper"]/button', single=False)
    clickIt(e[-2])

    feedback = readQuestFeedback(students)

    f = open(f'{course.replace("/","-")} :: {questName.replace("/","-")} - {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}.json', "w")
    f.write(str(feedback))
    f.close()

    if behavs:
        acknowledgeBehaviours(feedback)


def getTeams():
    DRIVER.get("https://game.classcraft.com/teacher/home")
    sleep(1)

    try:
        doClasscraftLogin(ccreds['user'], ccreds['password'])
    except Exception as e:
        print(e)
        pass

    openCourse(course)

    return True


def main(course: str, feedback: dict = None, quests: list = None, behavs: bool = False):
    DRIVER.get("https://game.classcraft.com/teacher/home")
    sleep(1)

    try:
        doClasscraftLogin(ccreds['user'], ccreds['password'])
    except Exception as e:
        print(e)
        pass

    openCourse(course)

    if feedback:
        print(feedback)
        acknowledgeBehaviours(feedback)
    else:
        if quests:
            for q in quests:
                giveQuestFeedback(questName=q, behavs=behavs)
        else:
            giveQuestFeedback(behavs=behavs)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="A script for opening a Classcraft class in a browser and applying behaviour based on completed assignments."
    )
    parser.add_argument("-c", "--courses", type=str, nargs="*",
                        default=["Demo"], help="Full name(s) or a part of the full name of the class(es). Default: 'Demo'")
    parser.add_argument("-q", "--quests", type=str, nargs="*",
                        default=None, help="Name(s) or a part of the name of the quest(s). Default: None")
    parser.add_argument("--grade", dest="grade", default=False, action="store_true",
                        help="Acknowledge (apply) behaviours as well. Default: False")
    parser.add_argument("--teams", dest="teams", default=False, action="store_true",
                        help="Store users and their teams in a file. It ignores all other options. Default: False. Not yet implemented")
    parser.add_argument("--gui", dest="gui", action="store_true", default=False, help="Show GUI. ")
    args = parser.parse_args()

    opt = Options()
    if not args.gui:
        opt.add_argument("--headless")
    opt.add_argument("--incognito")
    DRIVER = webdriver.Chrome(options=opt, executable_path="./chromedriver")

    for c in args.courses:
        if args.teams:
            getTeams(c)
            continue
        main(course=c, quests=args.quests, behavs=args.grade)

    DRIVER.quit()
