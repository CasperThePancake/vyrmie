# ================================================
# IMPORTS
# ================================================

import winsound
from textual.message import Message
from textual.widget import Widget

def beep(freq=1000):
    winsound.Beep(freq, 300)  # frequency Hz, duration ms

# Textual imports
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Static, Button, Rule, Input, Collapsible, TabbedContent, TabPane, Select, \
    Switch, ListView, ListItem, Label, TextArea, Tab, Tabs
from textual.containers import Vertical, Horizontal, Center, CenterMiddle, VerticalScroll
from textual import log, events
from textual.reactive import reactive
from textual.screen import Screen, ModalScreen
from textual import on

# Helper file imports
import non_textual as nt

# Other imports
from datetime import datetime, timedelta, date
import webbrowser
import urllib.parse

# ================================================
# MAIN VARIABLES
# ================================================
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
MONTH_SELECT = [("January",1), ("February",2), ("March", 3), ("April",4), ("May",5), ("June",6), ("July",7), ("August",8), ("September",9), ("October",10), ("November",11), ("December",12)]
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# ================================================
# CUSTOM WIDGETS
# ================================================

# Logbook edit button
class LogbookEditBtn(Static):
    def __init__(self, topic: str, entry: str, **kwargs):
        super().__init__("Edit", **kwargs)
        self.topic = topic
        self.entry = entry

    def on_click(self, event):
        event.stop()
        def after_confirm(confirm: tuple):
            if confirm:
                nt.edit_entry(self.topic,self.entry,confirm[0],confirm[1])
                self.app.screen.load_logbook()
        self.app.push_screen(LogbookEntryEdit(self.topic,self.entry),after_confirm)

# Logbook delete button
class LogbookDeleteBtn(Static):
    def __init__(self, topic: str, entry: str, **kwargs):
        super().__init__("Delete", **kwargs)
        self.topic = topic
        self.entry = entry

    def on_click(self, event):
        event.stop()
        self.post_message(LogbookMenu.DeleteEntry(self.topic, self.entry))

# Logbook buttons
class EntryButtons(Widget):
    DEFAULT_CSS = """
    .buttonHorizontal {
        height: auto;
    }
    
    EntryButtons .editBtn {
        width: auto;
        margin-right: 3;
    }
    
    EntryButtons .deleteBtn {
        width: auto;
    }
    
    """


    def __init__(self, topic: str, entry: str, **kwargs):
        super().__init__(**kwargs)
        self.topic = topic
        self.entry = entry

    def compose(self):
        with Horizontal(classes="buttonHorizontal"):
            yield LogbookEditBtn(self.topic, self.entry, classes="editBtn")
            yield LogbookDeleteBtn(self.topic, self.entry, classes="deleteBtn")

# Calendar week
class WeekView(Widget):
    DEFAULT_CSS = """
    WeekView {
        height: 1fr;
        layout: vertical;
    }

    #titleBar {
        height: 3;
        align-horizontal: center;
    }

    #weekTitle {
        width: 20%;
        border: round $primary;
        padding-left: 2;
        padding-right: 2;
    }

    #dayView {
        layout: horizontal;
        height: 1fr;
        width: 1fr;
    }
    
    DayColumn.today .day-header {
        background: $surface;
    }

    DayColumn {
        width: 1fr;
        height: 1fr;
        border-right: solid $surface-darken-2;
    }

    DayColumn:last-child {
        border-right: none;
    }

    .day-header {
        height: 3;
        content-align: center middle;
        background: $surface-darken-1;
        text-style: bold;
    }
    
    .day-split {
        height: auto;
        content-align: center middle;
        border-bottom: round $secondary;
    }

    .day-body {
        height: 1fr;
    }
    
    .shiftButton {
        width: auto;
        height: 3;
        content-align: center middle;
        padding: 0 1;
    }
    """

    def __init__(self, *children: Widget):
        super().__init__(*children)
        self.currentStartDate = None

    def refresh_calendar(self):
        self.load_week(self.currentStartDate)

    def go_to_today(self):
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        self.load_week(monday)

    def load_week(self,start_date: date):
        self.currentStartDate = start_date

        startingMonth = start_date.month
        startingYear = start_date.year

        for i in range(7):
            self.query_one(f"#day{i+1}").update_date(start_date)
            if i == 6:
                endingMonth = start_date.month
                endingYear = start_date.year
            start_date = start_date + timedelta(days=1)

        if startingMonth == endingMonth:
            self.query_one("#weekTitle").update(f"{MONTHS[startingMonth-1]} {startingYear}")
        else:
            self.query_one("#weekTitle").update(f"{MONTHS[startingMonth-1]} {startingYear} - {MONTHS[endingMonth-1]} {endingYear}")

    def on_click(self, event):
        event.stop()
        if event.widget.id == "leftButton":
            self.load_week(self.currentStartDate - timedelta(7))
        elif event.widget.id == "rightButton":
            self.load_week(self.currentStartDate + timedelta(7))

    def compose(self):
        with Horizontal(id="titleBar"):
            yield Static("‹", classes="shiftButton", id="leftButton")
            yield Static("May 2026", id="weekTitle", classes="center")
            yield Static("›", classes="shiftButton", id="rightButton")
        with Horizontal(id="dayView"):
            yield DayColumn(date.today(),id="day1")
            yield DayColumn(date.today(),id="day2")
            yield DayColumn(date.today(),id="day3")
            yield DayColumn(date.today(),id="day4")
            yield DayColumn(date.today(),id="day5")
            yield DayColumn(date.today(),id="day6")
            yield DayColumn(date.today(),id="day7")

    def on_mount(self):
        # Load the calendar for this week, starting on this week's monday
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        self.load_week(monday)

class DayColumn(Widget):
    def __init__(self, day: date, **kwargs):
        super().__init__(**kwargs)
        self.day = day
        self.events = self.app.calendarIndex[f"{day.year}-{day.month:02d}-{day.day:02d}"]

    def update_date(self,day: date):
        self.day = day
        self.events = self.app.calendarIndex[f"{day.year}-{day.month:02d}-{day.day:02d}"]
        self.query_one("#dayName").update(f"{WEEKDAYS[self.day.weekday()]} {self.day.day}")
        if "today" in self.classes:
            self.remove_class("today")
        if self.day == date.today():
            self.add_class("today")
            self.query_one("#dayName").update(f"{WEEKDAYS[self.day.weekday()]} {self.day.day} (today)")

        # Load event entries
        self.query_one("#dayEntryList").remove_children()
        for event in sorted(self.events, key=lambda x: f"{x["start_time"]["hour"]:02d}{x["start_time"]["minute"]:02d}"):
            self.query_one("#dayEntryList").mount(EventEntry(event,self.day))

        # Load task entries
        self.query_one("#dayTasksList").remove_children()
        tasks = self.app.taskCalendarIndex[f"{day.year}-{day.month:02d}-{day.day:02d}"]
        for task in tasks:
            self.query_one("#dayTasksList").mount(TaskEntryCalendar(task[1],task[0]))

    def on_click(self,event):
        event.stop()
        if event.widget.id == "dayEvents":
            def after_created(void):
                self.app.index_calendar()
            self.app.push_screen(EventCreation(),after_created)
        elif event.widget.id == "dayTasks":
            def on_create_task(void):
                self.app.index_tasksCalendar()
            self.app.push_screen(TaskCreation("taskMenuDailyTasks",self.day), callback=on_create_task)

    def compose(self):
        yield Static(f"{WEEKDAYS[self.day.weekday()]} {self.day.day}", classes="day-header",id="dayName")
        yield Static("Events",classes="day-split", id="dayEvents")
        yield VerticalScroll(classes="day-body", id="dayEntryList")
        yield Static("Tasks",classes="day-split", id="dayTasks")
        yield VerticalScroll(classes="day-body", id="dayTasksList")

# Event entry
class EventEntry(Static):
    DEFAULT_CSS = """
    EventEntry {
        margin-bottom: 1;
    }
    
    #eventTime {
        text-style: bold;
    }
    
    """

    def __init__(self, event: dict, linkedDate: date):
        super().__init__()
        self.event = event
        self.date = linkedDate
        self.role = nt.get_event_day_role(event,linkedDate)

    def compose(self):
        eventName = self.event["name"]
        if self.role == "middle":
            eventStartTime = {"hour": 0, "minute": 0}
            eventEndTime = {"hour": 23, "minute": 59}
        elif self.role == "start":
            eventStartTime = self.event["start_time"]
            eventEndTime = {"hour": 23, "minute": 59}
        elif self.role == "end":
            eventStartTime = {"hour": 0, "minute": 0}
            eventEndTime = self.event["end_time"]
        elif self.role == "single":
            eventStartTime = self.event["start_time"]
            eventEndTime = self.event["end_time"]
        if eventStartTime == {"hour": 0, "minute": 0} and eventEndTime == {"hour": 23, "minute": 59}:
            yield Static("Entire day",classes="center",id="eventTime")
        elif eventStartTime == {"hour": 0, "minute": 0}:
            yield Static(f"Until {eventEndTime["hour"]:02d}:{eventEndTime["minute"]:02d}",classes="center",id="eventTime")
        elif eventEndTime == {"hour": 23, "minute": 59}:
            yield Static(f"From {eventStartTime["hour"]:02d}:{eventStartTime["minute"]:02d}",classes="center",id="eventTime")
        else:
            yield Static(f"{eventStartTime["hour"]:02d}:{eventStartTime["minute"]:02d} - {eventEndTime["hour"]:02d}:{eventEndTime["minute"]:02d}",classes="center",id="eventTime")
        yield Static(f"{eventName}",id="eventTitle")

    def on_click(self, event):
        event.stop()
        self.app.push_screen(EventDetails(self.event,self.date))

# Event entry detailed view
class EventDetails(ModalScreen):
    def __init__(self, event: dict, linkedDate: date):
        super().__init__()
        self.event = event
        self.date = linkedDate

    def open_maps(self, query: str):
        url = f"https://www.google.com/maps/search/{urllib.parse.quote(query)}"
        webbrowser.open(url)

    DEFAULT_CSS = """
    EventDetails {
        align: center middle;
    }

    #dialog {
        width: 75%;
        height: 75%;
        border: round $primary;
        background: $surface;
        padding: 1 2;
    }
    
    #eventOptions #editBtn {
        color: sandybrown;
    }
    
    #eventOptions #deleteBtn {
        color: red;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static(self.event["name"],classes="center")
            yield Rule(line_style="solid")
            with Horizontal(id="eventOptions"):
                yield Static("Edit ✎",classes="eventDetailsBtn",id="editBtn")
                yield Static("Delete 🗙",classes="eventDetailsBtn",id="deleteBtn")
            yield Static(f"{self.event["description"]}\n")

            occurrence_start, occurrence_end = nt.get_event_day_occurrence(self.event,self.date)

            if occurrence_start == occurrence_end:
                d = occurrence_start
                yield Static(f"{d.strftime("%A %d %B %Y").lstrip("0")} from {self.event["start_time"]["hour"]:02d}:{self.event["start_time"]["minute"]:02d} to {self.event["end_time"]["hour"]:02d}:{self.event["end_time"]["minute"]:02d}\n")
            else:
                s_d = occurrence_start
                e_d = occurrence_end
                yield Static(f"{s_d.strftime("%A %d %B %Y").lstrip("0")} ({self.event["start_time"]["hour"]:02d}:{self.event["start_time"]["minute"]:02d}) to {e_d.strftime("%A %d %B %Y").lstrip("0")} ({self.event["end_time"]["hour"]:02d}:{self.event["end_time"]["minute"]:02d})\n")
            yield Static(f"🖈 {self.event["location"]}",id="eventLocation")

    def on_click(self, event):
        event.stop()
        dialog = self.query_one("#dialog")
        if not dialog.region.contains(event.screen_x, event.screen_y):
            self.app.pop_screen()
        elif event.widget.id == "eventLocation" and self.event["location"]:
            self.open_maps(self.event["location"])
        elif event.widget.id == "editBtn":
            def after_edit(void):
                self.app.index_calendar()
                self.app.pop_screen()
            self.app.push_screen(EventEdit(self.event), after_edit)
        elif event.widget.id == "deleteBtn":
            def handle_result(result: bool):
                if result != "cancel":
                    nt.delete_event(self.event,result,self.date)
                    self.app.index_calendar()
                    self.app.pop_screen()
            self.app.push_screen(EventDeletePopup(self.event), handle_result)

# Calendar task entry
class TaskEntryCalendar(Static):
    DEFAULT_CSS = """
    EventEntry {
        margin-bottom: 1;
    }
    """

    def __init__(self, task: dict, taskType: str):
        super().__init__()
        self.linkedTask = task
        self.taskType = taskType

    def compose(self):
        if self.taskType == "deadline":
            yield Static(f"[bold]Deadline:[/bold] {self.linkedTask["name"]}")
        else:
            yield Static(f"{self.linkedTask["name"]}")

    def on_click(self, event):
        event.stop()
        if self.taskType == "deadline":
            self.app.push_screen(TasksMenu("taskMenuDeadlines"))
        else:
            self.app.push_screen(TasksMenu())

# Task entry
class TaskEntry(Static):
    expanded = reactive(False)

    DEFAULT_CSS = """
    #details {
        display: none;
        height: auto;
    }
    
    #mainBar {
        height: auto;
    }
    
    #mainBar Static {
        width: auto;
    }
    
    #mainBar Button {
        min-width: 3;
        width: 3;
        height: 1;
        border: none;
        background: transparent;
    }
    
    #mainBar #complete-btn {
        color: lime;
    }
    
    #mainBar #edit-btn {
        color: sandybrown;
    }
    
    #mainBar #delete-btn {
        color: red;
    }
    
    #mainBar #uncomplete-btn {
        color: cornflowerblue;
    }
    
    #mainBar .icon-btn {
        padding-left: 3;
        padding-right: 3;
    }
    
    #mainBar #task-name {
        text-style: bold;
        padding-left: 3;
    }
    
    #details #task-desc {
        margin-top: 1;
        padding-left: 3;
    }
    
    #mainBar Button:focus {
        background: transparent;
        border: none;
    }

    #mainBar Button.-active {
        background: transparent;
        border: none;
    }
    
    TaskEntry {
        border: round $primary;
    }
    
    TaskEntry:hover {
        background: $primary 20%;
    }
    """

    def __init__(self, task, id: str | None = None):
        super().__init__(id=id)
        self.linkedTask = task
        if task["start_date"] == task["end_date"]:
            self.taskType = "daily_task"
        elif task["end_date"] is not None:
            self.taskType = "deadline"
        else:
            self.taskType = "general_task"

        if task["completed"]:
            self.taskType = "completed"

    def compose(self):
        if self.taskType == "daily_task":
            with Horizontal(id="mainBar"):
                yield Static(self.linkedTask["name"],id="task-name")
                yield Static("✓", id="complete-btn", classes="icon-btn")
                yield Static("✎", id="edit-btn", classes="icon-btn")
                yield Static("🗙", id="delete-btn", classes="icon-btn")
            with Vertical(id="details"):
                yield Static(self.linkedTask["description"],id="task-desc")
        elif self.taskType == "deadline":
            with Horizontal(id="mainBar"):
                if self.linkedTask["start_date"] is not None and date.fromisoformat(self.linkedTask["start_date"]) > date.today():
                    yield Static(self.linkedTask["name"]+f" (due {date.fromisoformat(self.linkedTask["end_date"]).strftime("%A %d %B %Y").lstrip("0")}, completable from {date.fromisoformat(self.linkedTask["start_date"]).strftime("%A %d %B %Y").lstrip("0")})",id="task-name")
                else:
                    yield Static(self.linkedTask["name"]+f" (due {date.fromisoformat(self.linkedTask["end_date"]).strftime("%A %d %B %Y").lstrip("0")})",id="task-name")
                yield Static("✓", id="complete-btn", classes="icon-btn")
                yield Static("✎", id="edit-btn", classes="icon-btn")
                yield Static("🗙", id="delete-btn", classes="icon-btn")
            with Vertical(id="details"):
                yield Static(self.linkedTask["description"],id="task-desc")
        elif self.taskType == "general_task":
            with Horizontal(id="mainBar"):
                if self.linkedTask["start_date"] is not None and date.fromisoformat(self.linkedTask["start_date"]) > date.today():
                    yield Static(self.linkedTask["name"]+f" (completable from {date.fromisoformat(self.linkedTask["start_date"]).strftime("%A %d %B %Y").lstrip("0")})",id="task-name")
                else:
                    yield Static(self.linkedTask["name"],id="task-name")
                yield Static("✓", id="complete-btn", classes="icon-btn")
                yield Static("✎", id="edit-btn", classes="icon-btn")
                yield Static("🗙", id="delete-btn", classes="icon-btn")
            with Vertical(id="details"):
                yield Static(self.linkedTask["description"],id="task-desc")
        elif self.taskType == "completed":
            with Horizontal(id="mainBar"):
                yield Static(self.linkedTask["name"],id="task-name")
                yield Static("↩", id="uncomplete-btn", classes="icon-btn")
                yield Static("🗙", id="delete-btn", classes="icon-btn")
            with Vertical(id="details"):
                yield Static(self.linkedTask["description"],id="task-desc")

    def on_click(self, event):
        event.stop()
        if event.widget.id == "complete-btn":
            nt.complete_task(self.app,self.linkedTask)
            self.app.screen.load_tasks()
            self.app.index_tasksCalendar()
        elif event.widget.id == "edit-btn":
            def after_edit(void):
                self.app.screen.load_tasks()
                self.app.index_tasksCalendar()
            self.app.push_screen(TaskEdit(self.linkedTask), after_edit)
        elif event.widget.id == "delete-btn":
            def handle_result(confirmed: bool):
                if confirmed:
                    nt.delete_task(self.linkedTask)
                    self.app.screen.load_tasks()
                    self.app.index_tasksCalendar()
            self.app.push_screen(ConfirmPopup("delete this task"), handle_result)
        elif event.widget.id == "uncomplete-btn":
            nt.uncomplete_task(self.app, self.linkedTask)
            self.app.screen.load_tasks()
            self.app.index_tasksCalendar()
        else:
            self.expanded = not self.expanded

    def watch_expanded(self):
        if self.expanded:
            self.query_one("#details").styles.display = "block"
        else:
            self.query_one("#details").styles.display = "none"

# Menu button list for apps
class MenuButtons(Static):
    @on(Button.Pressed, "#buttonTasks")
    def pressed_tasks(self):
        self.app.push_screen(TasksMenu())

    @on(Button.Pressed, "#buttonCalendar")
    def pressed_calendar(self):
        self.app.push_screen(CalendarMenu())

    @on(Button.Pressed, "#buttonLogbook")
    def pressed_logbook(self):
        self.app.push_screen(LogbookMenu())

    @on(Button.Pressed, "#buttonSettings")
    def pressed_settings(self):
        self.app.push_screen(SettingsMenu())

    def compose(self):
        with Center(id="appList"):
            yield Button("Calendar", id="buttonCalendar")
            yield Button("Tasks", id="buttonTasks")
            yield Button("Logbook", id="buttonLogbook")
            yield Button("Settings", id="buttonSettings")

# Tasks for today
class TasksToday(Static):
    def load_user(self):
        self.app.get_widget_by_id("welcomeTitle").update(f"{nt.time_welcome()}, {self.app.userData.get("userName")}! Today is {MONTHS[datetime.now().month-1]} {datetime.now().day}, {datetime.now().year}.")

    def load_tasks(self):
        tasks = nt.load_today_tasks()

        # Daily tasks
        daily = self.query_one("#dailyList")
        daily.remove_children()
        if len(tasks["daily"]) == 1:
            self.query_one("#collapsibleDaily").title = f"You have [bold]1 daily task[/]"
        else:
            self.query_one("#collapsibleDaily").title = f"You have [bold]{len(tasks["daily"])} daily tasks[/]"

        for dailyTask in tasks["daily"]:
            daily.mount(Static(f"{dailyTask["name"]}"))

        # Deadlines
        deadlines = self.query_one("#deadlineList")
        deadlines.remove_children()
        if len(tasks["deadline"]) == 1:
            self.query_one("#collapsibleDeadline").title = f"You have [bold]1 deadline[/]"
        else:
            self.query_one("#collapsibleDeadline").title = f"You have [bold]{len(tasks["deadline"])} deadlines[/]"

        for deadline in tasks["deadline"]:
            deadlines.mount(Static(f"{deadline["name"]}"))

        # General tasks
        generals = self.query_one("#generalList")
        generals.remove_children()
        if len(tasks["general"]) == 1:
            self.query_one("#collapsibleGeneral").title = f"You have [bold]1 general task[/]"
        else:
            self.query_one("#collapsibleGeneral").title = f"You have [bold]{len(tasks["general"])} general tasks[/]"

        for general in tasks["general"]:
            generals.mount(Static(f"{general["name"]}"))

    def compose(self):
        with Center(id="tasks"):
            with Center():
                yield Static("Your work for today",id="header")
            with Collapsible(title="You have [bold]0 daily tasks[/]",classes="collapsible",id="collapsibleDaily",collapsed=False):
                yield Vertical(id="dailyList")
            with Collapsible(title="You have [bold]0 deadlines[/]",classes="collapsible",id="collapsibleDeadline",collapsed=False):
                yield Vertical(id="deadlineList")
            with Collapsible(title="You have [bold]0 general tasks[/]",classes="collapsible",id="collapsibleGeneral",collapsed=False):
                yield Vertical(id="generalList")

    def on_click(self,event):
        event.stop()
        if event.widget.id == "header":
            self.app.push_screen(TasksMenu())

# Activities for today
class ActivitiesToday(Static):
    def load_activities(self):
        myEvents = self.app.calendarIndex[f"{date.today().year}-{date.today().month:02d}-{date.today().day:02d}"]
        self.query_one("#activitiesList").remove_children()
        if len(myEvents) == 0:
            self.query_one("#activitiesList").mount(Static("None...", classes="menuEventEntry"))
        for event in myEvents:
            role = nt.get_event_day_role(event,date.today())
            eventName = event["name"]
            if role == "middle":
                eventStartTime = {"hour": 0, "minute": 0}
                eventEndTime = {"hour": 23, "minute": 59}
            elif role == "start":
                eventStartTime = event["start_time"]
                eventEndTime = {"hour": 23, "minute": 59}
            elif role == "end":
                eventStartTime = {"hour": 0, "minute": 0}
                eventEndTime = event["end_time"]
            elif role == "single":
                eventStartTime = event["start_time"]
                eventEndTime = event["end_time"]
            if eventStartTime == {"hour": 0, "minute": 0} and eventEndTime == {"hour": 23, "minute": 59}:
                self.query_one("#activitiesList").mount(Static(f"[Entire day] {eventName}", classes="menuEventEntry"))
            elif eventStartTime == {"hour": 0, "minute": 0}:
                self.query_one("#activitiesList").mount(Static(f"[Until {eventEndTime["hour"]:02d}:{eventEndTime["minute"]:02d}] {eventName}", classes="menuEventEntry"))
            elif eventEndTime == {"hour": 23, "minute": 59}:
                self.query_one("#activitiesList").mount(Static(f"[From {eventStartTime["hour"]:02d}:{eventStartTime["minute"]:02d}] {eventName}", classes="menuEventEntry"))
            else:
                self.query_one("#activitiesList").mount(Static(f"[{eventStartTime["hour"]:02d}:{eventStartTime["minute"]:02d} - {eventEndTime["hour"]:02d}:{eventEndTime["minute"]:02d}] {eventName}", classes="menuEventEntry"))

    def compose(self):
        with Center(id="activities"):
            with Center():
                yield Static("Today's activities", id="header")
            yield Vertical(id="activitiesList")

    def on_click(self,event):
        event.stop()
        if event.widget.id == "header":
            self.app.push_screen(CalendarMenu())

# ================================================
# SCREENS
# ================================================

# Main menu
class Menu(Screen):
    BINDINGS = [  # key, action, description

    ]

    def on_screen_resume(self):
        if self.app.userData:
            self.query_one("#activitiesToday").load_activities()
            self.query_one("#tasksToday").load_tasks()

    def compose(self):
        yield Footer()
        yield Header(show_clock=True)
        yield Static(f"{nt.time_welcome()}, {self.app.userData.get("userName")}! Today is {MONTHS[datetime.now().month-1]} {datetime.now().day}, {datetime.now().year}.", id="welcomeTitle", classes="center top-header")
        yield Rule(line_style="double")
        with Horizontal(id="mainFrame"):
            with Vertical(id="vertButtons"):
                yield MenuButtons(id="menuButtons")
            with Vertical(id="vertTasks"):
                yield TasksToday(id="tasksToday")
            with Vertical(id="vertActivities"):
                yield ActivitiesToday(id="activitiesToday")

    # "action_" necessary for Textual to know it's an action method
    def action_toggle_dark_mode(self):
        if self.app.theme == "textual-dark":
            self.app.theme = "textual-light"
        else:
            self.app.theme = "textual-dark"

# User creation
class UserCreation(Screen):
    @on(Button.Pressed,"#userCreationButton")
    def pressUserCreate(self):
        nt.create_user_gen(self.app,self.query_one(Input).value)

    def compose(self):
        yield Footer()
        yield Header(show_clock=True)
        with CenterMiddle():
            yield Rule(line_style="heavy")
            yield Static("Welcome to Vyrmie",classes="center")
            yield Rule(line_style="heavy")
            yield Static("Let's create your profile\n",classes="center")
            yield Input(placeholder="Username",id="userNameInput")
            yield Rule(line_style="dashed")
            with Center():
                yield Button("Create",id="userCreationButton")

# Popup confirmation
class ConfirmPopup(ModalScreen):
    def __init__(self, confirmingAction: str):
        super().__init__()
        self.confirmingAction = confirmingAction

    DEFAULT_CSS = """
    ConfirmPopup {
        align: center middle;
    }

    #dialog {
        width: 50;
        height: 10;
        border: round $primary;
        background: $surface;
        padding: 1 2;
        align: center middle;
    }
    
    #confirmButtons {
        align: center middle;
    }
    
    #confirm {
        margin-right: 2;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static(f"Are you sure you want to {self.confirmingAction}?",classes="center")
            with Horizontal(id="confirmButtons"):
                yield Button("Confirm", id="confirm",classes="center")
                yield Button("Cancel", id="cancel",classes="center")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)

# Tasks menu
class TasksMenu(Screen):
    BINDINGS = [  # key, action, description
        ("escape", "app.pop_screen", "Go back"),
        ("n", "new_task", "New task"),
    ]

    def __init__(self, openTab="taskMenuDailyTasks"):
        super().__init__()
        self.openTab = openTab


    def compose(self):
        yield Footer()
        yield Header(show_clock=True)
        yield Static("Tasks",classes="center top-header")
        yield Rule(line_style="double")
        with TabbedContent(initial=self.openTab,id="taskTabbedContent"):
            with TabPane("Daily tasks",id="taskMenuDailyTasks"):
                yield VerticalScroll(id="dailyTasksList",classes="taskList")
            with TabPane("Deadlines",id="taskMenuDeadlines"):
                with VerticalScroll(id="deadlinesList", classes="taskList"):
                    with Collapsible(title="Cannot be completed yet",id="deadlinesCannot",collapsed=True):
                        yield VerticalScroll(id="deadlinesCannotList")
                    with Collapsible(title="Can be completed",id="deadlinesCan",collapsed=False):
                        yield VerticalScroll(id="deadlinesCanList")
            with TabPane("General tasks", id="taskMenuGeneralTasks"):
                with VerticalScroll(id="generalTasksList", classes="taskList"):
                    with Collapsible(title="Cannot be completed yet", id="generalTasksCannot", collapsed=True):
                        yield VerticalScroll(id="generalTasksCannotList")
                    with Collapsible(title="Can be completed", id="generalTasksCan", collapsed=False):
                        yield VerticalScroll(id="generalTasksCanList")
            with TabPane("Completed",id="taskMenuCompleted"):
                yield VerticalScroll(id="completedTasksList", classes="taskList")


    def on_mount(self):
        self.load_tasks()

    def load_tasks(self):
        # Get tasks list
        tasks = nt.get_tasks()

        # Specify type
        daily_tasks = tasks["daily_tasks"]
        deadlines = tasks["deadlines"]
        general_tasks = tasks["general_tasks"]
        completed_tasks = tasks["completed"]

        # Clear daily tasks
        self.query_one("#dailyTasksList").remove_children()

        # Load daily tasks
        if not len(daily_tasks) == 0:
            today = date.today()
            sorted_dates = sorted(daily_tasks)

            closest = min(sorted_dates, key=lambda d: abs((date.fromisoformat(d) - today).days))
            closestDOM = None

            for isodate in sorted_dates:
                d = date.fromisoformat(isodate)
                if d == today:
                    header = "Today"
                elif d == today - timedelta(days=1):
                    header = "Yesterday"
                elif d == today + timedelta(days=1):
                    header = "Tomorrow"
                elif abs((d - today).days) <= 6:
                    header = d.strftime("%A, %d %B").lstrip("0")
                else:
                    header = d.strftime("%A %d %B %Y").lstrip("0")
                if d == today:
                    self.query_one("#dailyTasksList").mount(Static(header,classes="center taskListDailyDate today"))
                else:
                    self.query_one("#dailyTasksList").mount(Static(header, classes="center taskListDailyDate"))
                for i in range(len(daily_tasks[isodate])):
                    if i == len(daily_tasks[isodate])-1 and isodate == closest:
                        closestDOM = TaskEntry(daily_tasks[isodate][i])
                        self.query_one("#dailyTasksList").mount(closestDOM)
                    else:
                        self.query_one("#dailyTasksList").mount(TaskEntry(daily_tasks[isodate][i]))

            # Scroll to the closest daily task
            closestDOM.scroll_visible(animate=False)
        else:
            self.query_one("#dailyTasksList").mount(Static("None...", classes="center"))

        # Clear deadlines
        self.query_one("#deadlinesCannotList").remove_children()
        self.query_one("#deadlinesCanList").remove_children()
        cannotContents, canContents = False, False

        # Load deadlines
        if not len(deadlines) == 0:
            today = date.today()
            for deadline in sorted(deadlines, key=lambda x: x["end_date"]):
                dueDate = date.fromisoformat(deadline["end_date"])
                if deadline["start_date"]:
                    fromDate = date.fromisoformat(deadline["start_date"])
                else:
                    fromDate = date.today()

                if fromDate <= today:
                    self.query_one("#deadlinesCanList").mount(TaskEntry(deadline))
                    canContents = True
                else:
                    self.query_one("#deadlinesCannotList").mount(TaskEntry(deadline))
                    cannotContents = True
            # Check for emptiness
            if not canContents:
                self.query_one("#deadlinesCanList").mount(Static("None...", classes="center"))
            if not cannotContents:
                self.query_one("#deadlinesCannotList").mount(Static("None...", classes="center"))
        else:
            self.query_one("#deadlinesCanList").mount(Static("None...", classes="center"))
            self.query_one("#deadlinesCannotList").mount(Static("None...", classes="center"))

        # Clear general tasks
        self.query_one("#generalTasksCannotList").remove_children()
        self.query_one("#generalTasksCanList").remove_children()
        cannotContents, canContents = False, False

        # Load general tasks
        if not len(general_tasks) == 0:
            today = date.today()
            for general_task in sorted(general_tasks, key=lambda x: x["name"]):
                if general_task["start_date"]:
                    fromDate = date.fromisoformat(general_task["start_date"])
                else:
                    fromDate = date.today()

                if fromDate <= today:
                    self.query_one("#generalTasksCanList").mount(TaskEntry(general_task))
                    canContents = True
                else:
                    self.query_one("#generalTasksCannotList").mount(TaskEntry(general_task))
                    cannotContents = True
            # Check for emptiness
            if not canContents:
                self.query_one("#generalTasksCanList").mount(Static("None...", classes="center"))
            if not cannotContents:
                self.query_one("#generalTasksCannotList").mount(Static("None...", classes="center"))
        else:
            self.query_one("#generalTasksCanList").mount(Static("None...", classes="center"))
            self.query_one("#generalTasksCannotList").mount(Static("None...", classes="center"))

        # Clear completed tasks
        self.query_one("#completedTasksList").remove_children()

        # Load completed tasks
        if not len(completed_tasks) == 0:
            for completed_task in completed_tasks:
                self.query_one("#completedTasksList").mount(TaskEntry(completed_task))
        else:
            self.query_one("#completedTasksList").mount(Static("None...",classes="center"))


    def action_new_task(self):
        def on_create_task(void):
            self.load_tasks()
            self.app.index_tasksCalendar()
        self.app.push_screen(TaskCreation(self.query_one("#taskTabbedContent").active), callback=on_create_task)

# New task creation
class TaskCreation(Screen):
    BINDINGS = [  # key, action, description
        ("escape", "app.pop_screen", "Cancel"),
    ]

    def __init__(self, currentWindow, givenDay=date.today()):
        super().__init__()
        self.currentWindow = currentWindow
        if currentWindow == "taskMenuDailyTasks":
            self.currentWindow = "dailyTask"
        elif currentWindow == "taskMenuDeadlines":
            self.currentWindow = "deadline"
        else:
            self.currentWindow = "generalTask"
        self.givenDay = givenDay

    @on(Button.Pressed, "#createTask")
    def createTask(self):
        tab = self.query_one("#taskCreationTabs").active
        try:
            if tab == "dailyTask":
                nt.add_task(self.app,
                    self.query_one("#dailyTaskName").value,
                    self.query_one("#dailyTaskDescription").value,
                    {"day": int(self.query_one("#dailyTaskDay").value), "month": int(self.query_one("#dailyTaskMonth").value), "year": int(self.query_one("#dailyTaskYear").value)},
                     {"day": int(self.query_one("#dailyTaskDay").value), "month": int(self.query_one("#dailyTaskMonth").value), "year": int(self.query_one("#dailyTaskYear").value)}
                )
            elif tab == "deadline":
                nt.add_task(self.app,
                    self.query_one("#deadlineTaskName").value,
                    self.query_one("#deadlineTaskDescription").value,
                    None,
                     {"day": int(self.query_one("#deadlineTaskDay").value), "month": int(self.query_one("#deadlineTaskMonth").value), "year": int(self.query_one("#deadlineTaskYear").value)}
                )
            elif tab == "generalTask":
                nt.add_task(self.app,
                    self.query_one("#generalTaskName").value,
                    self.query_one("#generalTaskDescription").value,
                    None,
                     None
                )
            else: # Custom
                nt.add_task(self.app,
                    self.query_one("#customTaskName").value,
                    self.query_one("#customTaskDescription").value,
                    {"day": int(self.query_one("#customTaskFromDay").value), "month": int(self.query_one("#customTaskFromMonth").value), "year": int(self.query_one("#customTaskFromYear").value)} if self.query_one("#customFromDateSwitch").value else None,
                     {"day": int(self.query_one("#customTaskToDay").value), "month": int(self.query_one("#customTaskToMonth").value), "year": int(self.query_one("#customTaskToYear").value)} if self.query_one("#customToDateSwitch").value else None
                )
        except Exception as e:
            self.app.display_errors(e.args[0])
        else:
            self.dismiss(None)

    @on(Switch.Changed, "#customFromDateSwitch")
    def switchedFromDateSwitch(self):
        switched_on = self.query_one("#customFromDateSwitch").value
        if not switched_on:
            self.query_one("#customFromDate").styles.visibility = "hidden"
            self.query_one("#customFromDateTitle").update("\nNo start date\n")
        else:
            self.query_one("#customFromDate").styles.visibility = "visible"
            self.query_one("#customFromDateTitle").update("\nCan complete from\n")

    @on(Switch.Changed, "#customToDateSwitch")
    def switchedToDateSwitch(self):
        switched_on = self.query_one("#customToDateSwitch").value
        if not switched_on:
            self.query_one("#customToDate").styles.visibility = "hidden"
            self.query_one("#customToDateTitle").update("\nNo end date\n")
        else:
            self.query_one("#customToDate").styles.visibility = "visible"
            self.query_one("#customToDateTitle").update("\nMust complete by\n")


    def compose(self):
        yield Footer()
        yield Header(show_clock=True)
        yield Rule(line_style="double")
        yield Static("Create new task", classes="center")
        yield Rule(line_style="double")
        with TabbedContent(initial=self.currentWindow,id="taskCreationTabs"):
            with TabPane("Daily task", id="dailyTask", classes="taskPane"):
                with Vertical():
                    yield Static("A task to be completed on the specified date\n",classes="center")
                    yield Input(placeholder="Task name",id="dailyTaskName")
                    yield Input(placeholder="Task description (optional)",id="dailyTaskDescription")
                    yield Static("\nComplete on\n",classes="center")
                    with Horizontal(id="dateInput"):
                        yield Input(placeholder="Day",type="integer",restrict=r"^(?:[1-9]|[12][0-9]|3[01])?$",classes="dateChooser",value=str(self.givenDay.day),id="dailyTaskDay")
                        yield Select(options=MONTH_SELECT,classes="dateChooser",allow_blank=False,value=self.givenDay.month,id="dailyTaskMonth")
                        yield Input(placeholder="Year", type="integer",classes="dateChooser",value=str(self.givenDay.year),id="dailyTaskYear")
            with TabPane("Deadline", id="deadline", classes="taskPane"):
                with Vertical():
                    yield Static("A task to be completed by the specified date\n", classes="center")
                    yield Input(placeholder="Task name",id="deadlineTaskName")
                    yield Input(placeholder="Task description (optional)",id="deadlineTaskDescription")
                    yield Static("\nComplete by\n", classes="center")
                    with Horizontal(id="dateInput"):
                        yield Input(placeholder="Day", type="integer", restrict=r"^(?:[1-9]|[12][0-9]|3[01])?$",
                                    classes="dateChooser", value=str(self.givenDay.day),id="deadlineTaskDay")
                        yield Select(options=MONTH_SELECT, classes="dateChooser", allow_blank=False,
                                     value=self.givenDay.month,id="deadlineTaskMonth")
                        yield Input(placeholder="Year", type="integer", classes="dateChooser",
                                    value=str(self.givenDay.year),id="deadlineTaskYear")
            with TabPane("General task", id="generalTask", classes="taskPane"):
                with Vertical():
                    yield Static("A general task with no dates attached\n", classes="center")
                    yield Input(placeholder="Task name",id="generalTaskName")
                    yield Input(placeholder="Task description (optional)",id="generalTaskDescription")
            with TabPane("Custom",id="custom", classes="taskPane"):
                with Vertical():
                    yield Static("A task with a custom time-frame for completion\n", classes="center")
                    yield Input(placeholder="Task name",id="customTaskName")
                    yield Input(placeholder="Task description (optional)",id="customTaskDescription")
                    with Horizontal():
                        with Vertical():
                            with Horizontal(id="dateSwitcher"):
                                yield Switch(value=True,id="customFromDateSwitch")
                                yield Static("\nCan complete from\n", classes="center", id="customFromDateTitle")
                            with Horizontal(classes="dateInputCustom", id="customFromDate"):
                                yield Input(placeholder="Day", type="integer", restrict=r"^(?:[1-9]|[12][0-9]|3[01])?$",
                                            classes="dateChooser", value=str(self.givenDay.day),id="customTaskFromDay")
                                yield Select(options=MONTH_SELECT, classes="dateChooser", allow_blank=False,
                                             value=self.givenDay.month,id="customTaskFromMonth")
                                yield Input(placeholder="Year", type="integer", classes="dateChooser",
                                            value=str(self.givenDay.year),id="customTaskFromYear")
                        with Vertical():
                            with Horizontal(id="dateSwitcher"):
                                yield Switch(value=True, id="customToDateSwitch")
                                yield Static("\nMust be completed by\n", classes="center", id="customToDateTitle")
                            with Horizontal(classes="dateInputCustom", id="customToDate"):
                                yield Input(placeholder="Day", type="integer", restrict=r"^(?:[1-9]|[12][0-9]|3[01])?$",
                                            classes="dateChooser", value=str(self.givenDay.day),id="customTaskToDay")
                                yield Select(options=MONTH_SELECT, classes="dateChooser", allow_blank=False,
                                             value=self.givenDay.month,id="customTaskToMonth")
                                yield Input(placeholder="Year", type="integer", classes="dateChooser",
                                            value=str(self.givenDay.year),id="customTaskToYear")

        with Center():
            yield Button("Create",id="createTask")

class TaskEdit(Screen):
    BINDINGS = [  # key, action, description
        ("escape", "app.pop_screen", "Cancel"),
    ]

    def __init__(self, originalTask):
        super().__init__()
        self.originalTask = originalTask

    @on(Button.Pressed, "#createTask")
    def edited_task(self):
        try:
            nt.edit_task(self.app,
                         self.originalTask,
                         self.query_one("#customTaskName").value,
                         self.query_one("#customTaskDescription").value,
                         {"year": int(self.query_one("#customTaskFromYear").value), "month": int(self.query_one("#customTaskFromMonth").value), "day": int(self.query_one("#customTaskFromDay").value)} if self.query_one("#customFromDateSwitch").value else None,
                         {"year": int(self.query_one("#customTaskToYear").value), "month": int(self.query_one("#customTaskToMonth").value), "day": int(self.query_one("#customTaskToDay").value)} if self.query_one("#customToDateSwitch").value else None
                )
        except Exception as e:
            self.app.display_errors(e.args[0])
        else:
            self.dismiss(None)

    def on_mount(self):
        self.switchedFromDateSwitch()
        self.switchedToDateSwitch()

    @on(Switch.Changed, "#customFromDateSwitch")
    def switchedFromDateSwitch(self):
        switched_on = self.query_one("#customFromDateSwitch").value
        if not switched_on:
            self.query_one("#customFromDate").styles.visibility = "hidden"
            self.query_one("#customFromDateTitle").update("\nNo start date\n")
        else:
            self.query_one("#customFromDate").styles.visibility = "visible"
            self.query_one("#customFromDateTitle").update("\nCan complete from\n")

    @on(Switch.Changed, "#customToDateSwitch")
    def switchedToDateSwitch(self):
        switched_on = self.query_one("#customToDateSwitch").value
        if not switched_on:
            self.query_one("#customToDate").styles.visibility = "hidden"
            self.query_one("#customToDateTitle").update("\nNo end date\n")
        else:
            self.query_one("#customToDate").styles.visibility = "visible"
            self.query_one("#customToDateTitle").update("\nMust complete by\n")

    def compose(self):
        yield Footer()
        yield Header(show_clock=True)
        yield Rule(line_style="double")
        yield Static("Edit task", classes="center")
        yield Rule(line_style="double")
        with Vertical():
            yield Input(placeholder="Task name", id="customTaskName",value=self.originalTask["name"])
            yield Input(placeholder="Task description (optional)", id="customTaskDescription",value=self.originalTask["description"])
            with Horizontal():
                start_date = date.fromisoformat(self.originalTask["start_date"]) if self.originalTask["start_date"] else None
                end_date = date.fromisoformat(self.originalTask["end_date"]) if self.originalTask["end_date"] else None
                with Vertical():
                    with Horizontal(id="dateSwitcher"):
                        yield Switch(value=(start_date is not None), id="customFromDateSwitch")
                        yield Static("\nCan complete from\n", classes="center", id="customFromDateTitle")
                    with Horizontal(classes="dateInputCustom", id="customFromDate"):
                        yield Input(placeholder="Day", type="integer", restrict=r"^(?:[1-9]|[12][0-9]|3[01])?$",
                                    classes="dateChooser", value=(str(datetime.now().day) if start_date is None else str(start_date.day)), id="customTaskFromDay")
                        yield Select(options=MONTH_SELECT, classes="dateChooser", allow_blank=False,
                                     value=(datetime.now().month if start_date is None else start_date.month), id="customTaskFromMonth")
                        yield Input(placeholder="Year", type="integer", classes="dateChooser",
                                    value=(str(datetime.now().year) if start_date is None else str(start_date.year)), id="customTaskFromYear")
                with Vertical():
                    with Horizontal(id="dateSwitcher"):
                        yield Switch(value=(end_date is not None), id="customToDateSwitch")
                        yield Static("\nMust be completed by\n", classes="center", id="customToDateTitle")
                    with Horizontal(classes="dateInputCustom", id="customToDate"):
                        yield Input(placeholder="Day", type="integer", restrict=r"^(?:[1-9]|[12][0-9]|3[01])?$",
                                    classes="dateChooser", value=(str(datetime.now().day) if end_date is None else str(end_date.day)), id="customTaskToDay")
                        yield Select(options=MONTH_SELECT, classes="dateChooser", allow_blank=False,
                                     value=(datetime.now().month if end_date is None else end_date.month), id="customTaskToMonth")
                        yield Input(placeholder="Year", type="integer", classes="dateChooser",
                                    value=(str(datetime.now().year) if end_date is None else str(end_date.year)), id="customTaskToYear")
        with Center():
            yield Button("Apply",id="createTask",classes="center")

class EventEdit(Screen):
    BINDINGS = [  # key, action, description
        ("escape", "app.pop_screen", "Cancel"),
    ]

    def __init__(self, event):
        super().__init__()
        self.event = event

    def on_mount(self):
        self.switchProcessing()

    @on(Button.Pressed, "#createTask")
    def createTask(self):
        try:
            # Delete old event
            nt.delete_event(self.event,"all",date.today()) # Date here is placeholder, we're just deleting the full thing so

            # Check if edits have influenced dates or repeating (if so --> exception rules are reset!)
            if self.event["start_date"] != f"{self.query_one("#eventFromYear").value}-{int(self.query_one("#eventFromMonth").value):02d}-{int(self.query_one("#eventFromDay").value):02d}" or self.event["end_date"] != f"{self.query_one("#eventToYear").value}-{int(self.query_one("#eventToMonth").value):02d}-{int(self.query_one("#eventToDay").value):02d}" or self.event["repeat"] != self.query_one("#eventRepeatsSelect").value:
                coreChanges = True
            else:
                coreChanges = False

            # Add new event
            end_switch = self.query_one("#toDateSwitch").value
            from_fullday_switch = self.query_one("#fromFullDaySwitch").value
            to_fullday_switch = self.query_one("#toFullDaySwitch").value
            if end_switch:
                if not coreChanges:
                    nt.add_event_full(
                        self.app,
                        self.query_one("#eventName").value,
                        self.query_one("#eventDescription").value,
                        self.query_one("#eventLocation").value,
                        f"{self.query_one("#eventFromYear").value}-{int(self.query_one("#eventFromMonth").value):02d}-{int(self.query_one("#eventFromDay").value):02d}",
                        f"{self.query_one("#eventToYear").value}-{int(self.query_one("#eventToMonth").value):02d}-{int(self.query_one("#eventToDay").value):02d}",
                        int(self.query_one("#eventFromHour").value) if not from_fullday_switch else 0,
                        int(self.query_one("#eventFromMinute").value) if not from_fullday_switch else 0,
                        int(self.query_one("#eventToHour").value) if not to_fullday_switch else 23,
                        int(self.query_one("#eventToMinute").value) if not to_fullday_switch else 59,
                        self.query_one("#eventRepeatsSelect").value,
                        self.event["repeat_end"],
                        self.event["repeat_exceptions"]
                    )
                else:
                    nt.add_event_full(
                        self.app,
                        self.query_one("#eventName").value,
                        self.query_one("#eventDescription").value,
                        self.query_one("#eventLocation").value,
                        f"{self.query_one("#eventFromYear").value}-{int(self.query_one("#eventFromMonth").value):02d}-{int(self.query_one("#eventFromDay").value):02d}",
                        f"{self.query_one("#eventToYear").value}-{int(self.query_one("#eventToMonth").value):02d}-{int(self.query_one("#eventToDay").value):02d}",
                        int(self.query_one("#eventFromHour").value) if not from_fullday_switch else 0,
                        int(self.query_one("#eventFromMinute").value) if not from_fullday_switch else 0,
                        int(self.query_one("#eventToHour").value) if not to_fullday_switch else 23,
                        int(self.query_one("#eventToMinute").value) if not to_fullday_switch else 59,
                        self.query_one("#eventRepeatsSelect").value
                    )
            else:
                if not coreChanges:
                    nt.add_event_full(
                        self.app,
                        self.query_one("#eventName").value,
                        self.query_one("#eventDescription").value,
                        self.query_one("#eventLocation").value,
                        f"{self.query_one("#eventFromYear").value}-{int(self.query_one("#eventFromMonth").value):02d}-{int(self.query_one("#eventFromDay").value):02d}",
                        f"{self.query_one("#eventFromYear").value}-{int(self.query_one("#eventFromMonth").value):02d}-{int(self.query_one("#eventFromDay").value):02d}",
                        int(self.query_one("#eventFromHour").value) if not from_fullday_switch else 0,
                        int(self.query_one("#eventFromMinute").value) if not from_fullday_switch else 0,
                        int(self.query_one("#eventToHour").value) if not from_fullday_switch else 23,
                        int(self.query_one("#eventToMinute").value) if not from_fullday_switch else 59,
                        self.query_one("#eventRepeatsSelect").value,
                        self.event["repeat_end"],
                        self.event["repeat_exceptions"]
                    )
                else:
                    nt.add_event_full(
                        self.app,
                        self.query_one("#eventName").value,
                        self.query_one("#eventDescription").value,
                        self.query_one("#eventLocation").value,
                        f"{self.query_one("#eventFromYear").value}-{int(self.query_one("#eventFromMonth").value):02d}-{int(self.query_one("#eventFromDay").value):02d}",
                        f"{self.query_one("#eventFromYear").value}-{int(self.query_one("#eventFromMonth").value):02d}-{int(self.query_one("#eventFromDay").value):02d}",
                        int(self.query_one("#eventFromHour").value) if not from_fullday_switch else 0,
                        int(self.query_one("#eventFromMinute").value) if not from_fullday_switch else 0,
                        int(self.query_one("#eventToHour").value) if not from_fullday_switch else 23,
                        int(self.query_one("#eventToMinute").value) if not from_fullday_switch else 59,
                        self.query_one("#eventRepeatsSelect").value
                    )
        except Exception as e:
            self.app.display_errors(e.args[0])
        else:
            self.dismiss(None)

    @on(Switch.Changed, "#toDateSwitch")
    def switchedToDateSwitch(self):
        self.switchProcessing()

    @on(Switch.Changed, "#fromFullDaySwitch")
    def switchedFromFullDaySwitch(self):
        self.switchProcessing()

    @on(Switch.Changed, "#toFullDaySwitch")
    def switchedToFullDaySwitch(self):
        self.switchProcessing()

    def switchProcessing(self):
        end_switch = self.query_one("#toDateSwitch").value
        from_fullday_switch = self.query_one("#fromFullDaySwitch").value
        to_fullday_switch = self.query_one("#toFullDaySwitch").value
        if end_switch: # Multi-day event
            # Show the date switcher
            self.query_one("#toFullDay").styles.visibility = "visible"
            self.query_one("#toDate").styles.visibility = "visible"
            self.query_one("#toDateTitle").update("\nEnd day\n")
            if from_fullday_switch:
                self.query_one("#fromTimeMain").styles.visibility = "hidden"
            else:
                self.query_one("#fromTimeMain").styles.visibility = "visible"
            if to_fullday_switch:
                self.query_one("#toTimeMain").styles.visibility = "hidden"
            else:
                self.query_one("#toTimeMain").styles.visibility = "visible"
        else:
            self.query_one("#toFullDay").styles.visibility = "hidden"
            self.query_one("#toDate").styles.visibility = "hidden"
            self.query_one("#toDateTitle").update("\nSingle-day\n")
            if from_fullday_switch:
                self.query_one("#fromTimeMain").styles.visibility = "hidden"
                self.query_one("#toTimeMain").styles.visibility = "hidden"
            else:
                self.query_one("#fromTimeMain").styles.visibility = "visible"
                self.query_one("#toTimeMain").styles.visibility = "visible"

    def compose(self):
        # Date determination
        if self.event["start_date"] == self.event["end_date"]:
            single = True
        else:
            single = False

        if self.event["start_time"] == {"hour": 0, "minute": 0}:
            from_full = True
        else:
            from_full = False

        if self.event["end_time"] == {"hour": 23, "minute": 59}:
            to_full = True
        else:
            to_full = False

        yield Footer()
        yield Header(show_clock=True)
        yield Rule(line_style="double")
        yield Static("Edit event", classes="center")
        yield Rule(line_style="double")
        with Vertical():
            # Name & description
            yield Input(placeholder="Event name",id="eventName",value=self.event["name"])
            yield Input(placeholder="Event description (optional)",id="eventDescription",value=self.event["description"])
            yield Input(placeholder="Event location (optional)",id="eventLocation",value=self.event["location"])
            # Dates
            with Horizontal():
                with Vertical():
                    with Horizontal(id="dateSwitcher"):
                        yield Static("\nStart date\n", classes="center", id="fromDateTitle")
                    with Horizontal(classes="dateInputEvent", id="fromDate"):
                        yield Input(placeholder="Day", type="integer", restrict=r"^(?:[1-9]|[12][0-9]|3[01])?$",
                                    classes="dateChooser", value=str(date.fromisoformat(self.event["start_date"]).day),id="eventFromDay")
                        yield Select(options=MONTH_SELECT, classes="dateChooser", allow_blank=False,
                                     value=date.fromisoformat(self.event["start_date"]).month,id="eventFromMonth")
                        yield Input(placeholder="Year", type="integer", classes="dateChooser",
                                    value=str(date.fromisoformat(self.event["start_date"]).year),id="eventFromYear")
                    with Horizontal(id="fromFullDay"):
                        yield Switch(value=from_full, id="fromFullDaySwitch")
                        yield Static("\nFull day\n", classes="center")
                with Vertical():
                    with Horizontal(id="dateSwitcher"):
                        yield Switch(value=not single, id="toDateSwitch")
                        yield Static("\nEnd date\n", classes="center", id="toDateTitle")
                    with Horizontal(classes="dateInputEvent", id="toDate"):
                        yield Input(placeholder="Day", type="integer", restrict=r"^(?:[1-9]|[12][0-9]|3[01])?$",
                                    classes="dateChooser", value=str(date.fromisoformat(self.event["start_date"]).day),id="eventToDay")
                        yield Select(options=MONTH_SELECT, classes="dateChooser", allow_blank=False,
                                     value=date.fromisoformat(self.event["start_date"]).month,id="eventToMonth")
                        yield Input(placeholder="Year", type="integer", classes="dateChooser",
                                    value=str(date.fromisoformat(self.event["start_date"]).year),id="eventToYear")
                    with Horizontal(id="toFullDay"):
                        yield Switch(value=to_full, id="toFullDaySwitch")
                        yield Static("\nFull day\n", classes="center")
            # Times
            with Horizontal():
                with Vertical(id="fromTimeMain"):
                    with Horizontal(id="timeSwitcher"):
                        yield Static("\nStart time\n", classes="center", id="fromTimeTitle")
                    with Horizontal(classes="timeInputEvent", id="fromTime"):
                        yield Input(placeholder="00", type="integer", restrict=r"^(?:[0-9]|[1][0-9]|2[0-3])?$",
                                    classes="timeChooser", value=str(self.event["start_time"]["hour"]),id="eventFromHour")
                        yield Input(placeholder="00", type="integer", restrict=r"^(?:[0-9]|[1-5][0-9])?$",
                                    classes="timeChooser", value=str(self.event["start_time"]["minute"]),id="eventFromMinute")
                with Vertical(id="toTimeMain"):
                    with Horizontal(id="timeSwitcher"):
                        yield Static("\nEnd time\n", classes="center", id="toTimeTitle")
                    with Horizontal(classes="timeInputEvent", id="toTime"):
                        yield Input(placeholder="00", type="integer", restrict=r"^(?:[0-9]|[1][0-9]|2[0-3])?$",
                                    classes="timeChooser", value=str(self.event["end_time"]["hour"]),id="eventToHour")
                        yield Input(placeholder="00", type="integer", restrict=r"^(?:[0-9]|[1-5][0-9])?$",
                                    classes="timeChooser", value=str(self.event["end_time"]["minute"]),id="eventToMinute")
            # Repeating
            with Horizontal(id="eventRepeatsMain"):
                yield Static("Repeats:",id="eventRepeatsTitle")
                yield Select([("No repeat",None),("Daily","daily"),("Weekly","weekly"),("Monthly","monthly"),("Yearly","year")],value=self.event["repeat"],allow_blank=False,id="eventRepeatsSelect")
        yield Static("Note: changing any date or repeat options will reset all deleted repeats of this event!",classes="center")
        with Center():
            yield Button("Apply",id="createTask")

class EventCreation(Screen):
    BINDINGS = [  # key, action, description
        ("escape", "app.pop_screen", "Cancel"),
    ]

    def __init__(self, givenDate: date = date.today()):
        super().__init__()
        self.givenDate = givenDate

    def on_mount(self):
        self.switchProcessing()

    @on(Button.Pressed, "#createTask")
    def createTask(self):
        try:
            end_switch = self.query_one("#toDateSwitch").value
            from_fullday_switch = self.query_one("#fromFullDaySwitch").value
            to_fullday_switch = self.query_one("#toFullDaySwitch").value
            if end_switch:
                nt.add_event_full(
                    self.app,
                    self.query_one("#eventName").value,
                    self.query_one("#eventDescription").value,
                    self.query_one("#eventLocation").value,
                    f"{self.query_one("#eventFromYear").value}-{int(self.query_one("#eventFromMonth").value):02d}-{int(self.query_one("#eventFromDay").value):02d}",
                    f"{self.query_one("#eventToYear").value}-{int(self.query_one("#eventToMonth").value):02d}-{int(self.query_one("#eventToDay").value):02d}",
                    int(self.query_one("#eventFromHour").value) if not from_fullday_switch else 0,
                    int(self.query_one("#eventFromMinute").value) if not from_fullday_switch else 0,
                    int(self.query_one("#eventToHour").value) if not to_fullday_switch else 23,
                    int(self.query_one("#eventToMinute").value) if not to_fullday_switch else 59,
                    self.query_one("#eventRepeatsSelect").value
                )
            else:
                nt.add_event_full(
                    self.app,
                    self.query_one("#eventName").value,
                    self.query_one("#eventDescription").value,
                    self.query_one("#eventLocation").value,
                    f"{self.query_one("#eventFromYear").value}-{int(self.query_one("#eventFromMonth").value):02d}-{int(self.query_one("#eventFromDay").value):02d}",
                    f"{self.query_one("#eventFromYear").value}-{int(self.query_one("#eventFromMonth").value):02d}-{int(self.query_one("#eventFromDay").value):02d}",
                    int(self.query_one("#eventFromHour").value) if not from_fullday_switch else 0,
                    int(self.query_one("#eventFromMinute").value) if not from_fullday_switch else 0,
                    int(self.query_one("#eventToHour").value) if not from_fullday_switch else 23,
                    int(self.query_one("#eventToMinute").value) if not from_fullday_switch else 59,
                    self.query_one("#eventRepeatsSelect").value
                )
        except Exception as e:
            self.app.display_errors(e.args[0])
        else:
            self.dismiss(None)

    @on(Switch.Changed, "#toDateSwitch")
    def switchedToDateSwitch(self):
        self.switchProcessing()

    @on(Switch.Changed, "#fromFullDaySwitch")
    def switchedFromFullDaySwitch(self):
        self.switchProcessing()

    @on(Switch.Changed, "#toFullDaySwitch")
    def switchedToFullDaySwitch(self):
        self.switchProcessing()

    def switchProcessing(self):
        end_switch = self.query_one("#toDateSwitch").value
        from_fullday_switch = self.query_one("#fromFullDaySwitch").value
        to_fullday_switch = self.query_one("#toFullDaySwitch").value
        if end_switch: # Multi-day event
            # Show the date switcher
            self.query_one("#toFullDay").styles.visibility = "visible"
            self.query_one("#toDate").styles.visibility = "visible"
            self.query_one("#toDateTitle").update("\nEnd day\n")
            if from_fullday_switch:
                self.query_one("#fromTimeMain").styles.visibility = "hidden"
            else:
                self.query_one("#fromTimeMain").styles.visibility = "visible"
            if to_fullday_switch:
                self.query_one("#toTimeMain").styles.visibility = "hidden"
            else:
                self.query_one("#toTimeMain").styles.visibility = "visible"
        else:
            self.query_one("#toFullDay").styles.visibility = "hidden"
            self.query_one("#toDate").styles.visibility = "hidden"
            self.query_one("#toDateTitle").update("\nSingle-day\n")
            if from_fullday_switch:
                self.query_one("#fromTimeMain").styles.visibility = "hidden"
                self.query_one("#toTimeMain").styles.visibility = "hidden"
            else:
                self.query_one("#fromTimeMain").styles.visibility = "visible"
                self.query_one("#toTimeMain").styles.visibility = "visible"

    def compose(self):
        yield Footer()
        yield Header(show_clock=True)
        yield Rule(line_style="double")
        yield Static("Create new event", classes="center")
        yield Rule(line_style="double")
        with Vertical():
            # Name & description
            yield Input(placeholder="Event name",id="eventName")
            yield Input(placeholder="Event description (optional)",id="eventDescription")
            yield Input(placeholder="Event location (optional)",id="eventLocation")
            # Dates
            with Horizontal():
                with Vertical():
                    with Horizontal(id="dateSwitcher"):
                        yield Static("\nStart date\n", classes="center", id="fromDateTitle")
                    with Horizontal(classes="dateInputEvent", id="fromDate"):
                        yield Input(placeholder="Day", type="integer", restrict=r"^(?:[1-9]|[12][0-9]|3[01])?$",
                                    classes="dateChooser", value=str(self.givenDate.day),id="eventFromDay")
                        yield Select(options=MONTH_SELECT, classes="dateChooser", allow_blank=False,
                                     value=self.givenDate.month,id="eventFromMonth")
                        yield Input(placeholder="Year", type="integer", classes="dateChooser",
                                    value=str(self.givenDate.year),id="eventFromYear")
                    with Horizontal(id="fromFullDay"):
                        yield Switch(value=False, id="fromFullDaySwitch")
                        yield Static("\nFull day\n", classes="center")
                with Vertical():
                    with Horizontal(id="dateSwitcher"):
                        yield Switch(value=False, id="toDateSwitch")
                        yield Static("\nEnd date\n", classes="center", id="toDateTitle")
                    with Horizontal(classes="dateInputEvent", id="toDate"):
                        yield Input(placeholder="Day", type="integer", restrict=r"^(?:[1-9]|[12][0-9]|3[01])?$",
                                    classes="dateChooser", value=str((self.givenDate + timedelta(days=1)).day),id="eventToDay")
                        yield Select(options=MONTH_SELECT, classes="dateChooser", allow_blank=False,
                                     value=(self.givenDate + timedelta(days=1)).month,id="eventToMonth")
                        yield Input(placeholder="Year", type="integer", classes="dateChooser",
                                    value=str((self.givenDate + timedelta(days=1)).year),id="eventToYear")
                    with Horizontal(id="toFullDay"):
                        yield Switch(value=False, id="toFullDaySwitch")
                        yield Static("\nFull day\n", classes="center")
            # Times
            with Horizontal():
                with Vertical(id="fromTimeMain"):
                    with Horizontal(id="timeSwitcher"):
                        yield Static("\nStart time\n", classes="center", id="fromTimeTitle")
                    with Horizontal(classes="timeInputEvent", id="fromTime"):
                        yield Input(placeholder="00", type="integer", restrict=r"^(?:[0-9]|[1][0-9]|2[0-3])?$",
                                    classes="timeChooser", value=str(datetime.now().hour),id="eventFromHour")
                        yield Input(placeholder="00", type="integer", restrict=r"^(?:[0-9]|[1-5][0-9])?$",
                                    classes="timeChooser", value="00",id="eventFromMinute")
                with Vertical(id="toTimeMain"):
                    with Horizontal(id="timeSwitcher"):
                        yield Static("\nEnd time\n", classes="center", id="toTimeTitle")
                    with Horizontal(classes="timeInputEvent", id="toTime"):
                        yield Input(placeholder="00", type="integer", restrict=r"^(?:[0-9]|[1][0-9]|2[0-3])?$",
                                    classes="timeChooser", value=str(datetime.now().hour+1),id="eventToHour")
                        yield Input(placeholder="00", type="integer", restrict=r"^(?:[0-9]|[1-5][0-9])?$",
                                    classes="timeChooser", value="00",id="eventToMinute")
            # Repeating
            with Horizontal(id="eventRepeatsMain"):
                yield Static("Repeats:",id="eventRepeatsTitle")
                yield Select([("No repeat",None),("Daily","daily"),("Weekly","weekly"),("Monthly","monthly"),("Yearly","year")],value=None,allow_blank=False,id="eventRepeatsSelect")
        with Center():
            yield Button("Create",id="createTask")

class InputErrorScreen(ModalScreen):
    DEFAULT_CSS = """
    InputErrorScreen {
        align: center middle;
    }

    #dialog {
        width: 50;
        height: auto;
        border: round $error;
        background: $error-darken-2;
        padding: 1 2;
        align: center middle;
    }

    #confirmButtons {
        align: center middle;
        height: auto;
    }
    
    #confirmButtons Button {
        background: $error-darken-2;
        border: round $error;
    }

    #confirm {
        margin-right: 2;
    }
    
    #errorTitle {
        text-style: bold;
    }
    
    #errorList {
        margin-bottom: 2;
        height: auto;
    }
    """

    def __init__(self, errors):
        super().__init__()
        self.errors = errors

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static(f"Your input raised errors:\n", classes="center",id="errorTitle")
            with Vertical(id="errorList"):
                for error in self.errors:
                    yield Static(f"- {error}")
            with Horizontal(id="confirmButtons"):
                yield Button("OK", id="confirm", classes="center")

    def on_button_pressed(self, event: Button.Pressed):
        self.app.pop_screen()

class CalendarMenu(Screen):
    BINDINGS = [  # key, action, description
        ("escape", "app.pop_screen", "Go back"),
        ("r", "go_to_today", "Go to today"),
        ("n", "create_new", "New event")
    ]

    def on_screen_resume(self) -> None:
        self.query_one("WeekView").refresh_calendar()

    def action_create_new(self):
        def after_created(void):
            self.app.index_calendar()
            self.query_one("WeekView").refresh_calendar()
        self.app.push_screen(EventCreation(),after_created)

    def action_go_to_today(self):
        self.query_one("WeekView").go_to_today()

    def compose(self):
        yield Footer()
        yield Header()
        yield Static("Calendar",classes="center top-header")
        yield Rule(line_style="double")
        yield WeekView()

class EventDeletePopup(ModalScreen):
    def __init__(self, event: dict):
        super().__init__()
        self.event = event

    DEFAULT_CSS = """
    EventDeletePopup {
        align: center middle;
    }

    #dialog {
        width: 50;
        height: 15;
        border: round $primary;
        background: $surface;
        padding: 1 2;
        align: center middle;
    }
    
    #confirmButtons {
        align: center middle;
    }
    
    #confirm {
        margin-right: 2;
    }
    
    #repeatOption {
        margin-top: 2;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static(f"Are you sure you want to delete this event?",classes="center")
            if self.event["repeat"]:
                yield Select(options=[("This event","this"),("This and following events","following"),("All events","all")],allow_blank=False,value="this",id="repeatOption")
            with Horizontal(id="confirmButtons"):
                yield Button("Confirm", id="confirm",classes="center")
                yield Button("Cancel", id="cancel",classes="center")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm":
            if self.event["repeat"]:
                self.dismiss(self.query_one("#repeatOption").value)
            else:
                self.dismiss(None)
        else:
            self.dismiss("cancel")

# New topic modal screen
class TopicCreation(ModalScreen):
    DEFAULT_CSS = """
    TopicCreation {
        align: center middle;
    }

    #dialog {
        width: 50;
        height: 15;
        border: round $primary;
        background: $surface;
        padding: 1 2;
        align: center middle;
    }
    
    #confirmButtons {
        align: center middle;
    }
    
    #confirm {
        margin-right: 2;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static("Create new logbook topic\n",classes="center")
            yield Input(placeholder="Topic name",id="topicTitle")
            with Horizontal(id="confirmButtons"):
                yield Button("Add",id="confirm")
                yield Button("Cancel",id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm":
            self.dismiss(self.query_one("#topicTitle").value)
        else:
            self.dismiss(None)

# New entry modal screen
class EntryCreation(ModalScreen):
    DEFAULT_CSS = """
    EntryCreation {
        align: center middle;
    }

    #dialog {
        width: 50;
        height: 25;
        border: round $primary;
        background: $surface;
        padding: 1 2;
        align: center middle;
    }
    
    #confirmButtons {
        align: center middle;
    }
    
    #confirm {
        margin-right: 2;
    }
    
    #entryText {
        height: 10;
        min-height: 10;
        max-height: 10;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static("Create new entry\n",classes="center")
            yield Input(placeholder="Entry title",id="entryTitle")
            yield TextArea(placeholder="Entry text",id="entryText")
            with Horizontal(id="confirmButtons"):
                yield Button("Add",id="confirm")
                yield Button("Cancel",id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm":
            self.dismiss((self.query_one("#entryTitle").value,self.query_one("#entryText").text))
        else:
            self.dismiss(None)

# Logbook screen
class LogbookMenu(Screen):
    DEFAULT_CSS = """
    .topicVertical {
        height: auto;
    }
    
    .deleteBtn {
        color: $error;
    }
    
    .editBtn {
        color: sandybrown;
    }
    
    .buttonsHorizontal {
        height: auto;
    }
    
    """

    BINDINGS = [  # key, action, description
        ("escape", "app.pop_screen", "Go back"),
        ("n", "new_topic", "New topic"),
        ("r", "edit_topic", "Edit selected topic"),
        ("del", "del_topic", "Delete selected topic"),
        ("enter", "new_entry", "New entry"),
        ("p","export_logbook","Export as HTML"),
    ]

    def action_export_logbook(self):
        nt.export_logbook()

    def action_edit_topic(self):
        tabs = self.query_one("#tabs", TabbedContent)
        active_id = tabs.active  # "tab-1"
        for tab in tabs.query(Tab):
            if tab.id == f"--content-tab-{active_id}":
                topic = str(tab.label)
                break
        def after_confirm(result):
            if result:
                nt.edit_topic(topic,result)
                self.load_logbook()
        self.app.push_screen(LogbookTopicEdit(topic),after_confirm)

    def action_del_topic(self):
        tabs = self.query_one("#tabs", TabbedContent)
        active_id = tabs.active  # "tab-1"
        for tab in tabs.query(Tab):
            if tab.id == f"--content-tab-{active_id}":
                topic = str(tab.label)
                break
        def after_confirm(confirm):
            if confirm:
                nt.delete_topic(topic)
                self.load_logbook()
        self.app.push_screen(ConfirmPopup("delete the selected topic"),after_confirm)

    def action_new_topic(self):
        def after_confirm(result):
            if result:
                nt.add_topic(result)
                self.load_logbook()
        self.app.push_screen(TopicCreation(),after_confirm)


    def action_new_entry(self):
        tabs = self.query_one("#tabs", TabbedContent)
        active_id = tabs.active  # "tab-1"
        for tab in tabs.query(Tab):
            if tab.id == f"--content-tab-{active_id}":
                topic = str(tab.label)
                break
        def after_confirm(result):
            if result:
                nt.add_entry(topic,result[0],result[1])
                self.load_logbook()
        self.app.push_screen(EntryCreation(),after_confirm)

    def load_logbook(self):
        self.run_worker(self._load_logbook_async())

    async def _load_logbook_async(self):
        logbook = nt.get_logbook()
        tabs = self.query_one("#tabs", TabbedContent)
        await tabs.clear_panes()
        for topic_key in sorted(logbook):
            children = [
                Collapsible(
                    EntryButtons(topic_key, entry, classes="buttonsHorizontal"),
                    Static(logbook[topic_key][entry]),
                    title=entry
                )
                for entry in sorted(logbook[topic_key])
            ]
            await tabs.add_pane(TabPane(topic_key,Vertical(*children, classes="topicVertical")))

    def on_mount(self):
        self.load_logbook()

    def compose(self):
        yield Footer()
        yield Header(show_clock=True)
        yield Static("Logbook",classes="center top-header")
        yield Rule(line_style="double")
        yield TabbedContent(id="tabs")

    class DeleteEntry(Message):
        def __init__(self, topic: str, entry: str):
            super().__init__()
            self.topic = topic
            self.entry = entry

    @on(DeleteEntry)
    def handle_delete(self, message: DeleteEntry):
        def handle_confirm(confirmed: bool):
            if confirmed:
                nt.delete_entry(message.topic,message.entry)
                self.load_logbook()
        self.app.push_screen(ConfirmPopup("delete this entry"),handle_confirm)

# Logbook topic editing
class LogbookTopicEdit(ModalScreen):
    DEFAULT_CSS = """
    LogbookTopicEdit {
        align: center middle;
    }

    #dialog {
        width: 50;
        height: 15;
        border: round $primary;
        background: $surface;
        padding: 1 2;
        align: center middle;
    }
    
    #confirmButtons {
        align: center middle;
    }
    
    #confirm {
        margin-right: 2;
    }
    """

    def __init__(self, topic: str):
        super().__init__()
        self.topic = topic

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static("Edit logbook topic\n",classes="center")
            yield Input(placeholder="Topic name",value=self.topic,id="topicTitle")
            with Horizontal(id="confirmButtons"):
                yield Button("Apply",id="confirm")
                yield Button("Cancel",id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm":
            self.dismiss(self.query_one("#topicTitle").value)
        else:
            self.dismiss(None)

# Logbook entry editing
class LogbookEntryEdit(ModalScreen):
    DEFAULT_CSS = """
    LogbookEntryEdit {
        align: center middle;
    }

    #dialog {
        width: 50;
        height: 25;
        border: round $primary;
        background: $surface;
        padding: 1 2;
        align: center middle;
    }
    
    #confirmButtons {
        align: center middle;
    }
    
    #confirm {
        margin-right: 2;
    }
    
    #entryText {
        height: 10;
        min-height: 10;
        max-height: 10;
    }
    """

    def __init__(self, topic_key, entry):
        super().__init__()
        self.topic_key = topic_key
        self.entry = entry

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static("Edit entry\n",classes="center")
            yield Input(placeholder="Entry title",value=self.entry,id="entryTitle")
            yield TextArea(placeholder="Entry text",text=nt.get_entry(self.topic_key,self.entry),id="entryText")
            with Horizontal(id="confirmButtons"):
                yield Button("Apply",id="confirm")
                yield Button("Cancel",id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm":
            self.dismiss((self.query_one("#entryTitle").value,self.query_one("#entryText").text))
        else:
            self.dismiss(None)

# Settings menu
class SettingsMenu(Screen):
    BINDINGS = [  # key, action, description
        ("escape", "app.pop_screen", "Go back"),
    ]

    def compose(self):
        yield Footer()
        yield Header(show_clock=True)
        yield Static("Settings",classes="center top-header")
        yield Rule(line_style="double")
        yield Static("Settings menu is work-in-progress...",classes="center")

# ================================================
# APP
# ================================================
class Vyrmie(App):
    BINDINGS = [  # key, action, description
        ("escape", "quit", "Quit"),
    ]

    ENABLE_COMMAND_PALETTE = False
    ALLOW_SELECT = False

    SCREENS = {
        "main": Menu,
        "userCreation": UserCreation,
    }

    def __init__(self):
        super().__init__()
        self.calendarIndex = None
        self.taskCalendarIndex = None
        self.userData = nt.DEFAULT_USER

    def on_mount(self):
        self.push_screen("main")
        self.theme = "nord"
        self.userData = nt.load_user(self)
        if self.userData:
            self.index_calendar()
            self.index_tasksCalendar()
        if self.userData: # Update widget if loaded
            self.get_widget_by_id("tasksToday").load_user()

    def display_errors(self,errors):
        self.push_screen(InputErrorScreen(errors))

    def index_calendar(self):
        self.calendarIndex = nt.build_calendar_index()

    def index_tasksCalendar(self):
        self.taskCalendarIndex = nt.build_taskCalendar_index()

    CSS_PATH = "vyrmie.css"
    pass

# ================================================
# RUN MAIN
# ================================================
if __name__ == "__main__":
    Vyrmie().run()