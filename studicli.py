#!/usr/bin/python
# -*- coding: utf-8 -*-
# Required packages: argparse pyquery

__author__ = "Johannes Maximimilian Toball"
__license__ = "by-sa"

from argparse import ArgumentParser
from urllib2 import urlopen, build_opener, Request, HTTPCookieProcessor, HTTPRedirectHandler
from cookielib import CookieJar, LWPCookieJar
from pyquery import PyQuery as pq
from calendar import day_name 
from getpass import getpass
from datetime import date
import pickle
import types
import sys
import os
from asciioutput import ASCIIOutput
from utils import br2nl, fromQueryString, selectId, safeName

# Configure Command Line Options
argParser = ArgumentParser("Rudimentary command line client for Stud.IP as in use at the University of Passau.\n")
argParser.add_argument("--user", required=True, help="Stud.IP User", dest="user" )
argParser.add_argument("--pass",  help="Stud.IP User Password", dest="passwd" )
argParser.add_argument("--domain", required=True, help="Stud.IP User Domain", dest="domain",
                      choices=["stud", "fakult", "rz", "verw", "ub", "sonst"] )
argParser.add_argument("--action", required=True, help="Desired Action", dest="action", choices=["tt", "timetable", "readposts", "rp", "readnews", "rn", "readmessages", "rm", "download", "dl", "courselist", "cl", "writemessage", "wm"] )
argParser.add_argument("--only-new", help="Restrict action to newest entries (currently only applies to new files)", action="store_true", default=False, dest="only_new" )
argParser.add_argument("--all", help="Run action on all items, e.g. courses", action="store_true", default=False, dest="all" )
args = argParser.parse_args()

# URL to prepend to requests
baseUrl = "https://studip.uni-passau.de/studip/"
# Filenames
cookieFilename = ".cookies.lwp"
courseFilename = ".courses.tmp"

class StudICLI:
  """ StudICLI, a simple command line client class for Stud.IP as in use at the university
    of Passau """

  def __init__(self, user):
    # Touch files
    open(cookieFilename, "a").close()
    open(courseFilename, "a").close()

    # Init data
    self.loggedIn = False
    self.asciiout = ASCIIOutput(80)
    self.user = user 
    self.courses = {}
    self.cache = self.loadCache()
    self.cookies = self.initCookies()    


  def initCookies(self):
    """ Stud.IP requires cookies for session-handling.
      Cookies are stored in a file to limit login requests"""
    cookieFile = open(cookieFilename, "r+")
    cookies = LWPCookieJar(cookieFile.name)

    if len(cookieFile.read()) > 0:
      cookies.load(cookieFile.name, ignore_discard=True)
    return cookies
  
  def loadCache(self):
    # Courses are temporarily stored to limit requests
    courseFile = open(courseFilename, "rb+")

    if len(courseFile.read()) > 0:
      courseFile.seek(0)
      data = pickle.load(courseFile)
      
      # The cache is per-user
      if self.user != data["user"]:
        # Invalidate cached cookies
        open(cookieFilename, "w").close()
        data["courses"] = {}
      else:
        self.courses = data["courses"]
      return data
    return {"courses":{}, "user":""}


  def loadCourses(self):
    # Dictionary of courses.
    courses = {}
        # Rely on the cache if it contains entries, read courses from page otherwise
    storedCourses = self.cache["courses"]

    if type(storedCourses) == types.DictType and len(storedCourses) > 0:
      courses = storedCourses

    if len(courses) == 0:
      coursePage = pq(self.read("meine_seminare.php"))
      courseLinks = coursePage("td.blank").siblings("td a[href^=seminar]")

      def addCourse(id):
        """ inner function to process courses """
        courseName = courseLinks.eq(id).children("font").eq(0).text()

        if courseName != None:
          courseId = courseLinks.eq(id).attr("href").replace("seminar_main.php?auswahl=", "")
          courses[courseId] = courseName.strip()
      courseLinks.each(addCourse)
      # Storing the username with the courses allows for invalidation (see loadCache)
      data = {"courses": courses, "user": self.user}      
      courseFile = open(courseFilename, "rb+")
      pickle.dump(data, courseFile)
      courseFile.close()
      self.courses = courses

    return courses


  def req(self, url, body="", headers={}):
    """ Requests an URL, sends a body via POST and includess arbitrary header options
      This function is cookie- and redirect-aware"""
    request = Request(baseUrl+url, body, headers)
    opener = build_opener(HTTPRedirectHandler(), HTTPCookieProcessor(self.cookies))
    response = opener.open(request)
    #print request.get_full_url(), request.header_items()
    #print request.get_data()
    self.cookies.extract_cookies(response, request)
    self.cookies.save(ignore_discard=True)
    return response

  
  def read(self, url, body="", headers={}):
    """ read() is a shortcut to req([..]).read() to save some typing of this often used function """
    response = self.req(url, body, headers)
    return response.read()


  def login(self, user, passwd, domain):
    """ Execute an Login to Stud.IP. This requires two requests, 
      because the form includes an unique ID."""
    loginPage = pq(self.read("login.php"))

    # If there is no form element on the login page, we are already logged in
    loginTicket = loginPage("form input[name=login_ticket]").attr("value")
    loginArgs = "username="+user+"&password="+passwd
    loginArgs += "&userdomain=" +domain+"&login_ticket="+loginTicket
    loginResult = self.req("index.php", body=loginArgs)
    loggedIn = True
    
    self.loadCourses()
    return True


  def isLoggedIn(self):
    """ Calls the login page to see if the session is alive """
    loginPage = pq(self.read("login.php"))
    return not bool(loginPage("form").eq(0))


  def courselist(self, indexed=True, standalone=False):
    """ List courses and display details on demand """
    self.asciiout.h1("Meine Veranstaltungen")

    """ Prints a list of courses """
    for i in range(0, len(self.courses)):
      key = self.courses.keys()[i]

      if indexed:
        print "["+str(i)+"]  "+self.courses[key]
      else:
        print self.courses[key]
    
    # courselist() is also utilized by other actions. the standalone flag prevents conflicts
    if standalone:
      courseId = selectId("Veranstaltungsdetails", len(self.courses))  
      coursePage = pq(self.read("seminar_main.php?auswahl="+self.courses.keys()[courseId]))
      detailPage= pq(self.read("print_seminar.php"))
      self.asciiout.h1(detailPage("h1").eq(0).text())
      rows = detailPage("table").eq(0).find("tr")
      for i in range(1, len(rows)):
        tds = rows.eq(i).children("td")
        self.asciiout.h2(tds.eq(0).text())
        self.asciiout.text(br2nl(tds.eq(1)).text())

  def timetable(self):
    """ Prints a timetable """
    self.asciiout.h1("Mein Stundenplan")
    timetablePage = pq(self.read("mein_stundenplan.php"))
    coursePlan = timetablePage("#content table table tr td.rahmen_white")
    days = [[], [], [], [], [], [], []]
    lineSize = [2]

    def scheduleCourse(id):
      """ inner function that adds each course to the timetable. """
      course = coursePlan.eq(id) 
      infos = course.children("table td font")
      timeNroom = infos[0].text_content()
      event = infos[1].text_content()
      lineSize.append(len(event))
      teacher = infos[2].text_content()
      day = len(course.prevAll())-1
      days[day].append((timeNroom, event, teacher))

    coursePlan.each(scheduleCourse)
    self.asciiout.hr()

    for day in range(0, len(days)):
      """ Locale-dependent output of weekday. While it makes little sense with the
        hardcoded German strings everywhere, we avoid typing the names. """
      self.asciiout.h2(day_name[day])

      for course in days[day]:
        print course[1]  
        print course[0]  
        print "gelesen von: "+course[2]
        self.asciiout.hr()


  def download(self, new=False, all=False):
    """ Download files of a course"""
    courseId = 0
    if not all:
      cli.courselist()
      courseId = selectId("Veranstaltung", len(self.courses) -1)
    self.asciiout.h1("Dateien herunterladen")
    idRange = range(0, len(self.courses)) if all else [courseId]

    for id in idRange:  
      filePage = pq(self.read("seminar_main.php?auswahl="+self.courses.keys()[id]+"&redirect_to=plugins.php&cmd=show&id=19&view=seminarFolders"))
      keyword = ("Neue Dateien " if new else "")+"komprimiert herunterladen"
      downloadLink = filePage('a[title="'+keyword+'"]').eq(0).attr("href")
      courseName = self.courses[self.courses.keys()[id]]

      if downloadLink != None:
        print "Lade Dateien in '"+courseName+"' herunter"
        data = self.read(downloadLink.replace(baseUrl, ""))

        if len(data) > 0:
          fileName = "Downloads/"+safeName(courseName)+".zip"
          if not os.path.exists("Downloads"):
            os.makedirs("Downloads")
          f = open(fileName, "w+")
          f.write(data)
          f.close()
          self.asciiout.text("Dateien in '"+courseName+"' unter "+fileName+" gespeichert")
          self.asciiout.hr()
          continue
      self.asciiout.text("Keine Dateien in '"+courseName+"' gefunden")
      self.asciiout.hr()


  def readnews(self, all=False):
    """ Read news for a Course """
    cli.courselist()

    if not all:
      courseId = selectId("Veranstaltung", len(cli.courses) -1)
    width = 70
    idRange = range(0, len(self.courses)) if all else [courseId]

    for id in idRange:  
      self.asciiout.h1("News fuer "+self.courses[self.courses.keys()[id]]+" anzeigen")
      newsPage = pq(self.read("seminar_main.php?nclose=TRUE&auswahl="+self.courses.keys()[id]))
      newsItems = newsPage("a[href*=nopen]").children("img").parent()

      def printNews(i):
        """ inner function that prints course news """
        newsId = fromQueryString(newsItems.eq(i).attr("href"), "nopen")
        newsPage = pq(self.read("seminar_main.php?nopen="+newsId))
        title, rest = newsPage("a[href*=nclose]").parent().siblings().text().split("|", 1)
        self.asciiout.h2(title)
        self.asciiout.text(br2nl(newsPage("td.printcontent").eq(1)).text())
        self.asciiout.hr()
      newsItems.each(printNews)


  def readposts(self, all=False):
    """ Read posts from a course's messaging boards """  
    print cli.courselist()
    courseId = selectId("Veranstaltung", len(cli.courses) -1)
    self.asciiout.h1("Posts anzeigen")
    width = 70
    idRange = range(0, len(self.courses)) if all else [courseId]

    for id in idRange:  
      forumPage = pq(self.read("seminar_main.php?auswahl="+self.courses.keys()[id]+"&redirect_to=forum.php&view=reset&sort=age"))
      postsPage = pq(self.read("forum_export.php"))
      posts = postsPage("table td")
      self.asciiout.h1(self.courses[self.courses.keys()[id]])

      # Iterate through the Table with steps of 2. i is the headline, i+1 the body of the post
      for i in [x for x in range(0, len(posts)-2) if x % 2 ==0]:
        # Forum headlines have h3-tags
        forum = posts.eq(i).children("h3").text()

        if forum:
          self.asciiout.h2(forum)
        else:
          head = posts.eq(i).text()
          self.asciiout.h3(head)
          br2nl(posts.eq(i+1))
          body = posts.eq(i+1).text()
          self.asciiout.text(body)
          self.asciiout.hr()


  def readmessages(self, all=False):
    """ Read all or one message from the messaging system """
    self.asciiout.h1("Nachrichten lesen")
    messagePage = pq(self.read("sms_box.php?mclose=TRUE"))
    subjects = messagePage("td.printhead a.tree[href*=mopen]")
    messages = {}

    def messageList(id):
      subject = subjects.eq(id)
      author, date = subject.parents("td.printhead").eq(0).next().text().split(",", 1)
      messages[id] = { "hash" : fromQueryString(subject.attr("href"), "mopen"),
               "subject": subject.text(),
               "author": author.strip().replace("von ", ""),
               "date": date.strip()}

      if not all:
        print self.asciiout.trim("["+str(id)+"]  "+messages[id]["author"]+": "+subject.text())
    subjects.each(messageList)

    if not all:
      id = selectId("Nachricht", len(messages)-1)
      messages = {id: messages[id]}

    for message in messages:
      messagePage = pq(self.read("sms_box.php?mopen="+messages[message]['hash']))
      msg = messages[message]
      self.asciiout.h2(msg["author"]+": "+msg["subject"]+" ("+msg["date"]+")")
      self.asciiout.text(br2nl(messagePage("td.printcontent")).text()+"\n")

      if not all:
        respond = raw_input("Auf diese Nachricht anworten? [j/N] ")

        if respond in ["j", "J", "y", "Y"]:
          self.writemessage(answerTo=msg["hash"])
        
  
  def writemessage(self, recipient="", answerTo=""):
    """ Send message to another Stud.IP user """
    self.asciiout.h1("Nachricht schicken")

    if not len(recipient):

      if len(answerTo) == 0:
        recipient = raw_input("Empfänger: ")
        subject = raw_input("Betreff: ")
        self.read("sms_send.php", body="&add_freesearch.x=5&add_freesearch.y=11&add_freesearch&freesearch[]="+recipient)
      else:
        responsePage = pq(self.read("sms_send.php?cmd=write&answer_to="+answerTo))
        subject = responsePage("form input[name=messagesubject]").attr("value") 
      body = ""
      emptyLines = 0

      print "Nachricht (Mit zwei Leerzeilen abschließen): "
      while emptyLines < 2:
        line = raw_input()
        body += line+"\n"

        if len(line):
          emptyLines = 0 
        else:
          emptyLines += 1
      body.strip() # Strip the extra lines
      args = "messagesubject="+subject+"&message="+body+"&cmd_insert.x=1&cmd_insert.y=1"

      if len(answerTo) > 0:
        args += "answerTo"+answerTo
      response = self.read("sms_send.php", body=args)

      if response.find("wurde verschickt!") != -1:
        print "Nachricht erfolgreich verschickt"
      else:
        print "Nachricht konnte nicht verschickt werden"
  
  # TODO: Post to messageboard
  # TODO: Parse planner (look for an javascript handler?)
  # TODO: Increase robustness, handle errors
  # TODO: More exotic testcases, more extensive testing
  # TODO: Toggle caching
  # TODO: Single file downloads
  # TODO: Join-Course-Bot :D
  # TODO: Understand Stud.IP (possibly won't fix) 

# Instantiate the class    
cli = StudICLI(args.user)

# Execute Actions according to commandline options
action = args.action

try:
  # All Actions require a valid Session
  if not cli.isLoggedIn():

    for i in range(0, 3):

      while not args.passwd or not len(args.passwd) > 0 :
        args.passwd = getpass("Passwort eingeben: ")

      # Perform a Login
      cli.login(args.user, args.passwd, args.domain)
      if cli.isLoggedIn():
        break
      else:
        args.passwd = ""

      # Too many failed attempts, abort
      if i >= 2:
        sys.exit()

  if action in ["download", "dl"]: # Download files from courses
    cli.download(all=args.all, new=args.only_new)

  elif action in ["timetable", "tt"]: # Generate a timetable
    cli.timetable()

  elif action in ["courselist", "cl"]: # List courses 
    cli.courselist(standalone=True)

  elif action in ["readnews", "rn"]: # Read news from the course page
    cli.readnews(all=args.all)

  elif action in ["readposts", "rp"]: # Read posts from message boards
    cli.readposts()

  elif action in ["readmessages", "rm"]: # Read messages
    cli.readmessages(all=args.all)

  elif action in ["writemessage", "rm"]: # Write a message
    cli.writemessage()
except KeyboardInterrupt:
  print "\nAbbruch" 
