# ================================================
# IMPORTS
# ================================================
import os
import json
from collections import defaultdict

os.chdir(os.path.dirname(os.path.abspath(__file__)))

import winsound
def beep(freq=1000):
    winsound.Beep(freq, 300)  # frequency Hz, duration ms

from datetime import datetime, date, timedelta

DEFAULT_USER = {
    "userName": "UNSET"
}

def create_user(app):
    app.push_screen("userCreation")

def load_user(app):
    if not os.path.exists("userData.json"):
        create_user(app)
        return None
    try:
        with open("userData.json", "r", encoding="utf-8") as file:
            data = json.load(file)
        return data
    except json.JSONDecodeError:
        print("Error: the JSON is corrupted! Prompting new user creation.")
        create_user(app)
        return None

def create_user_gen(app,userName):
    # Form dictionary
    userData = {
        "userName": userName,
        "tasks": {
            "daily_tasks": {},
            "deadlines": [],
            "general_tasks": [],
            "completed": []
        },
        "events": {},
        "logbook": {"General": {}}
    }

    # Create json
    try:
        with open("userData.json", "w", encoding="utf-8") as file:
            # indent=4 makes the JSON pretty and easy for humans to read
            json.dump(userData, file, indent=4, ensure_ascii=False)
    except IOError as e:
        print(f"Error saving data: {e}")

    # pop the userCreation
    app.pop_screen()

    # run load_user
    app.userData = load_user(app)
    app.index_calendar()
    if app.userData:  # Update widget if loaded
        app.get_widget_by_id("tasksToday").load_user()

def time_welcome():
    currentHour = datetime.now().hour
    if currentHour < 4 or currentHour > 21:
        return "Good night"
    if 4 <= currentHour <= 12:
        return "Good morning"
    if 12 < currentHour <= 17:
        return "Good afternoon"
    if 17 < currentHour <= 21:
        return "Good evening"
    return "Welcome back"

def add_task(app,name,description,start_date,end_date):
    task = {
        "name": name,
        "description": description,
        "start_date": f"{start_date["year"]}-{start_date["month"]:02d}-{start_date["day"]:02d}" if start_date else None,
        "end_date": f"{end_date["year"]}-{end_date["month"]:02d}-{end_date["day"]:02d}" if end_date else None,
        "completed": False
    }

    errors = task_errors(task)
    if errors:
        raise Exception(errors)

    if start_date == end_date and start_date is not None:
        category = "daily_tasks"
    elif end_date is not None:
        category = "deadlines"
    else:
        category = "general_tasks"

    with open("userData.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    if category == "daily_tasks":
        fullDate = f"{start_date["year"]}-{start_date["month"]:02d}-{start_date["day"]:02d}"
        if fullDate in data["tasks"]["daily_tasks"]:
            data["tasks"]["daily_tasks"][fullDate].append(task)
        else:
            data["tasks"]["daily_tasks"][fullDate] = [task]
    else:
        data["tasks"][category].append(task)

    with open("userData.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def task_errors(task):
    errorList = []

    # Catch all the mistakes
    if len(task["name"]) == 0:
        errorList.append("Task name cannot be empty")

    if task["start_date"]:
        try:
            startDate = date.fromisoformat(task["start_date"])
        except ValueError:
            errorList.append("Start date is not a valid date")
            startDate = None
    else:
        startDate = None

    if task["end_date"]:
        try:
            endDate = date.fromisoformat(task["end_date"])
        except ValueError:
            errorList.append("End date is not a valid date")
            endDate = None
    else:
        endDate = None

    if startDate and endDate:
        if endDate < startDate:
            errorList.append("Start date must be before or on end date")

    # Return 'em
    if len(errorList) > 0:
        return errorList
    return None

def get_tasks():
    with open("userData.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    return data["tasks"]

def delete_task(task):
    # Load user data
    with open("userData.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    # Determine task type
    if task["start_date"] == task["end_date"] and task["start_date"] is not None:
        category = "daily_tasks"
    elif task["end_date"] is not None:
        category = "deadlines"
    else:
        category = "general_tasks"

    if task["completed"]:
        category = "completed"

    if category == "daily_tasks":
        data["tasks"]["daily_tasks"][task["start_date"]].remove(task)
        if len(data["tasks"]["daily_tasks"][task["start_date"]]) == 0:
            del data["tasks"]["daily_tasks"][task["start_date"]]
    else:
        data["tasks"][category].remove(task)

    # Save user data
    with open("userData.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def edit_task(app,originalTask, newTask_name,newTask_description,newTask_start_date,newTask_end_date):
    # Delete the original task
    delete_task(originalTask)

    # Add the new task (or try to)
    try:
        add_task(app,newTask_name,newTask_description,newTask_start_date,newTask_end_date)
    except Exception as e:
        # Re-add the original task
        add_task(app,originalTask["name"],originalTask["description"],{"day": date.fromisoformat(originalTask["start_date"]).day, "month": date.fromisoformat(originalTask["start_date"]).month,"year":date.fromisoformat(originalTask["start_date"]).year} if originalTask["start_date"] else None,{"day": date.fromisoformat(originalTask["end_date"]).day, "month": date.fromisoformat(originalTask["end_date"]).month,"year":date.fromisoformat(originalTask["end_date"]).year} if originalTask["end_date"] else None)

        # Raise the exception for deeper handling
        raise e

def complete_task(app,task):
    # Delete the task
    delete_task(task)

    # Add it to confirmed list (prepend)
    with open("userData.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    task["completed"] = True

    data["tasks"]["completed"].insert(0, task)

    with open("userData.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def uncomplete_task(app,task):
    # Remove from completed list
    with open("userData.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    data["tasks"]["completed"].remove(task)

    with open("userData.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    # Uncomplete and re-add
    task["completed"] = False

    add_task(app,task["name"],task["description"],{"day": date.fromisoformat(task["start_date"]).day, "month": date.fromisoformat(task["start_date"]).month,"year":date.fromisoformat(task["start_date"]).year} if task["start_date"] else None,{"day": date.fromisoformat(task["end_date"]).day, "month": date.fromisoformat(task["end_date"]).month,"year":date.fromisoformat(task["end_date"]).year} if task["end_date"] else None)

def add_event_full(app, event_title, event_description, event_location, event_startDate, event_endDate, event_startTime_hour, event_startTime_minute, event_endTime_hour, event_endTime_minute, event_repeatType, repeat_end=None,repeat_exceptions=None):
    if repeat_exceptions is None:
        repeat_exceptions = []
    with open("userData.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    event = {
        "name": event_title,
        "description": event_description,
        "location": event_location,
        "start_date": event_startDate,
        "end_date": event_endDate,
        "start_time": {"hour": event_startTime_hour, "minute": event_startTime_minute},
        "end_time": {"hour": event_endTime_hour, "minute": event_endTime_minute},
        "repeat": event_repeatType,
        "repeat_end": repeat_end,
        "repeat_exceptions": repeat_exceptions if repeat_exceptions else []
    }

    # Check for input errors
    errors = event_errors(event)
    if errors:
        raise Exception(errors)

    if event_startDate in data["events"]:
        data["events"][event_startDate].append(event)
    else:
        data["events"][event_startDate] = [event]

    with open("userData.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def add_event(app,event):
    # Check for input errors
    errors = event_errors(event)
    if errors:
        raise Exception(errors)

    with open("userData.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    if event["start_date"] in data["events"]:
        data["events"][event["start_date"]].append(event)
    else:
        data["events"][event["start_date"]] = [event]

    with open("userData.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def event_errors(event):
    errorList = []

    # Catch all the mistakes
    if len(event["name"]) == 0:
        errorList.append("Event name cannot be empty")

    try:
        startDate = date.fromisoformat(event["start_date"])
    except ValueError:
        errorList.append("Start date is not a valid date")
        startDate = None

    try:
        endDate = date.fromisoformat(event["end_date"])
    except ValueError:
        errorList.append("End date is not a valid date")
        endDate = None

    if startDate and endDate:
        if endDate < startDate:
            errorList.append("Start date must be before or on end date")

    duration = (date.fromisoformat(event["end_date"]) - date.fromisoformat(event["start_date"])).days

    max_duration = {
        "daily": 0,
        "weekly": 6,
        "monthly": 27,
        "yearly": 364,
    }

    if event["repeat"] and duration > max_duration[event["repeat"]]:
        errorList.append("Length of repeating event must not exceed repeat window")

    # Return 'em
    if len(errorList) > 0:
        return errorList
    return None

def build_calendar_index() -> dict:
    with open("userData.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    index = defaultdict(list)
    today = date.today()
    repeat_horizon = today.replace(year=today.year + 2)

    for date_key in data["events"]:
        for event in data["events"][date_key]:
            start = date.fromisoformat(event["start_date"])
            end = date.fromisoformat(event["end_date"])
            repeat = event.get("repeat")
            repeat_end = date.fromisoformat(event["repeat_end"]) if event.get("repeat_end") else None
            exceptions = set(event.get("repeat_exceptions", []))

            if not repeat:
                d = start
                while d <= end:
                    index[d.isoformat()].append(event)
                    d += timedelta(days=1)
            else:
                d = start
                while True:
                    if repeat_end and d >= repeat_end:
                        break
                    if d > repeat_horizon:
                        break
                    if d.isoformat() not in exceptions:
                        occurrence_start = d
                        occurrence_end = end + (d - start)
                        od = occurrence_start
                        while od <= occurrence_end:
                            index[od.isoformat()].append(event)
                            od += timedelta(days=1)
                    if repeat == "daily":
                        d += timedelta(days=1)
                    elif repeat == "weekly":
                        d += timedelta(weeks=1)
                    elif repeat == "monthly":
                        month = d.month + 1 if d.month < 12 else 1
                        year = d.year + (1 if d.month == 12 else 0)
                        d = d.replace(year=year, month=month)
                    elif repeat == "yearly":
                        d = d.replace(year=d.year + 1)
                    else:
                        break

    return index

def get_event_day_role(event, target_date):
    # We assume that the target_date is definitely related to the event, just not sure how
    start = date.fromisoformat(event["start_date"])
    end = date.fromisoformat(event["end_date"])
    duration = end - start

    if not event.get("repeat"):
        occurrence_start = start
        occurrence_end = end
    else:
        if event["repeat"] == "weekly":
            weeks = (target_date - start).days // 7
            occurrence_start = start + timedelta(weeks=weeks)
        elif event["repeat"] == "daily":
            occurrence_start = target_date
        elif event["repeat"] == "monthly":
            months = (target_date.year - start.year) * 12 + (target_date.month - start.month)
            month = (start.month + months - 1) % 12 + 1
            year = start.year + (start.month + months - 1) // 12
            occurrence_start = start.replace(year=year, month=month)
        elif event["repeat"] == "yearly":
            occurrence_start = start.replace(year=target_date.year)
        occurrence_end = occurrence_start + duration

    if occurrence_start == occurrence_end == target_date:
        return "single"
    elif target_date == occurrence_start:
        return "start"
    elif target_date == occurrence_end:
        return "end"
    else:
        return "middle"

def get_event_day_occurrence(event, target_date):
    # We assume that the target_date is definitely related to the event, just not sure how
    start = date.fromisoformat(event["start_date"])
    end = date.fromisoformat(event["end_date"])
    duration = end - start

    if not event.get("repeat"):
        occurrence_start = start
        occurrence_end = end
    else:
        if event["repeat"] == "weekly":
            weeks = (target_date - start).days // 7
            occurrence_start = start + timedelta(weeks=weeks)
        elif event["repeat"] == "daily":
            occurrence_start = target_date
        elif event["repeat"] == "monthly":
            months = (target_date.year - start.year) * 12 + (target_date.month - start.month)
            month = (start.month + months - 1) % 12 + 1
            year = start.year + (start.month + months - 1) // 12
            occurrence_start = start.replace(year=year, month=month)
        elif event["repeat"] == "yearly":
            occurrence_start = start.replace(year=target_date.year)
        occurrence_end = occurrence_start + duration

    return occurrence_start, occurrence_end

def delete_event(event, repeatDeleteType, linkedDate):
    occurrence_start, _ = get_event_day_occurrence(event, linkedDate)

    with open("userData.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    event_list = data["events"].get(event["start_date"], [])
    match = next((x for x in event_list if x["name"] == event["name"] and x["start_date"] == event["start_date"]), None)

    if match is None:
        return

    if event["repeat"]:
        if repeatDeleteType == "this":
            exc = f"{occurrence_start.year}-{occurrence_start.month:02d}-{occurrence_start.day:02d}"
            match["repeat_exceptions"].append(exc)
        elif repeatDeleteType == "following":
            match["repeat_end"] = f"{occurrence_start.year}-{occurrence_start.month:02d}-{occurrence_start.day:02d}"
        elif repeatDeleteType == "all":
            event_list.remove(match)
            if not event_list:
                del data["events"][event["start_date"]]
    else:
        event_list.remove(match)
        if not event_list:
            del data["events"][event["start_date"]]

    with open("userData.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def build_taskCalendar_index():
    with open("userData.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    index = defaultdict(list)

    # Daily tasks
    for keyDay in data["tasks"]["daily_tasks"]:
        index[keyDay].extend([("daily",task) for task in data["tasks"]["daily_tasks"][keyDay]])

    # Deadlines
    for deadline in data["tasks"]["deadlines"]:
        day = deadline["end_date"]
        index[day].append(("deadline",deadline))

    return index

def load_today_tasks():
    today = date.today()
    todayISO = f"{today.year}-{today.month:02d}-{today.day:02d}"
    output = {"daily": [], "deadline": [], "general": []}

    with open("userData.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    # Daily tasks
    if todayISO in data["tasks"]["daily_tasks"]:
        output["daily"] = data["tasks"]["daily_tasks"][todayISO]
    else:
        output["daily"] = []

    # Deadlines
    for deadline in data["tasks"]["deadlines"]:
        end_day = deadline["end_date"]
        from_day = deadline["start_date"]
        if not from_day or today >= date.fromisoformat(from_day):
            if today <= date.fromisoformat(end_day): # Good to add!
                output["deadline"].append(deadline)

    # General tasks
    for general_task in data["tasks"]["general_tasks"]:
        from_day = general_task["start_date"]
        if not from_day or today >= date.fromisoformat(from_day): # Good to add!
            output["general"].append(general_task)

    return output

def get_logbook():
    with open("userData.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    return data["logbook"]

def delete_entry(topic: str, entry: str):
    with open("userData.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    del data["logbook"][topic][entry]

    with open("userData.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def add_entry(topic: str, entryTitle: str, entryContent: str):
    with open("userData.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    data["logbook"][topic][entryTitle] = entryContent

    with open("userData.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def add_topic(topic: str):
    with open("userData.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    if not topic in data["logbook"]:
        data["logbook"][topic] = {}

    with open("userData.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def delete_topic(topic: str):
    with open("userData.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    del data["logbook"][topic]

    with open("userData.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_entry(topic: str, entry: str):
    with open("userData.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    return data["logbook"][topic][entry]

def edit_entry(topic: str, old_entry: str, new_entry: str, new_content: str):
    with open("userData.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    del data["logbook"][topic][old_entry]

    data["logbook"][topic][new_entry] = new_content

    with open("userData.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def edit_topic(old_topic: str, new_topic: str):
    with open("userData.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    data["logbook"][new_topic] = data["logbook"][old_topic]
    del data["logbook"][old_topic]

    with open("userData.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)