# cmw-wizard
> Automate Classcraft and Moodle Workshop using this Wizard

`Classcraft.py` and `Moodle.py` are the two main files here.

`Moodle.py` automates some actions (all optional) of Moodle's [Workshop](https://docs.moodle.org/310/en/Workshop_activity) activity, e.g.:

- auto-download of all submittion files + renaming them as course acronym - workshop's name - student's name, e.g. `MAS - Assignment 1 - Alice Babbage.zip` -- only one file supported;
- detect statistical outliers in grades received by assignments (optionally setting their weight values to 0);
- detect students who submitted assignments but gave no grades (optionally reducing their total received grade to 70%);
- receive a subset of 15% randomly selected assignments (e.g. for manually grading);
- receive a list of names of students who submitted top 10% of the graded assignments (points for grades given are not accounted for, only grades received);
- receive a list of names of students who submitted bottom 10% of the graded assignments (points for grades given are not accounted for, only grades received);
- store grades to Google Sheets;
- apply pre-defined behaviours in Classcraft, positive or negative behaviour, to the top and bottom 10% of the graded assignments.

`Classcraft.py` automates some actions of the gamified e-learning platform [Classcraft](https://www.classcraft.com), e.g.:

- detect students who submitted the final assignment of a quest:
  - early,
  - on time,
  - late,
  - never;
- according to the time when students submitted their assignment of the last task of a quest, apply specific positive or negative behaviours to individual students;
- apply specific behaviours from a given JSON containing names of students, indicator of positive or negative behaviours and the serial number of the applicable behaviour.

Help on using the defined arguments of either `Classcraft.py` or `Moodle.py` can be printed out using `-h`.

Specific methods defined within either of the base files can be used externally, although the `DRIVER` must usually be defined.

`Classcraft.py` generates a `.json` file with the behaviours it applied. `Moodle.py` generates a `.txt` file with its results.

# Requirements

The following non-default Python3 modules are used:

* `selenium` - requires [`chromedriver`](https://chromedriver.chromium.org/downloads) to be located in the folder of either `Classcraft.py` or `Moodle.py`
* `pyautogui`
* `pyperclip`
* `numpy`
* [`gspread`](https://github.com/burnash/gspread) - requires extra setup of Google Sheets API

Moodle and Classcraft login credentials are stored in file `credentials.py` as:

```
creds = {
    "user": "username",
    "password": "p4ssw0rd"
} # Moodle login

ccreds = {
    "user": "username",
    "password": "p4ssw0rd"
} # Classcraft login
```

#
