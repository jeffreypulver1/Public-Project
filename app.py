import os
from datetime import datetime
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, usd


# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///FTOE.db")

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/", methods=["GET"])
@login_required
def index():
    if request.method == "GET":
         location = db.execute("SELECT DISTINCT DESTINATION FROM PerDiem ORDER BY DESTINATION")
         airfare = db.execute("SELECT DISTINCT AIRFARE FROM CityPair")
         return render_template("createtrips.html", location=location, airfare=airfare)

@app.route("/create", methods=["GET", "POST"])
@login_required
def create():
    """Create Trip"""
    if request.method == "POST":
        tripname = request.form.get("tripname")
        if not request.form.get("tripname"):
            return apology("must provide a trip name", 400)
        rows = db.execute("SELECT DISTINCT * FROM trips WHERE id =? AND tripname = ?", session["user_id"], tripname)
        # Ensure tripname does not exist
        if len(rows) != 0:
            return apology("tripname already exists", 400)

        numtravelers = request.form.get("numtravelers")
        startdate = request.form.get("startdate")
        enddate = request.form.get("enddate")
        state = request.form.get("state")
        datediff = datetime.strptime(enddate, '%Y-%m-%d') - datetime.strptime(startdate, '%Y-%m-%d')
        datediff = datediff.days+1
        location = request.form.get("location")
        airfare2 = request.form.get("airfare")
        start = datetime.strptime(startdate, '%Y-%m-%d')
        start = start.month
        perdiem = db.execute("SELECT [M&IE] as mie, [Lodging Rate] as lodging FROM PerDiem WHERE DESTINATION = ? AND (seasonbegin IS NULL OR seasonbegin<=?) AND (seasonend iS NULL OR seasonend>=?)", location, start, start)
        lodging = float(perdiem[0]["lodging"])*(datediff-1)*int(numtravelers)
        mie = float(perdiem[0]["mie"])*(datediff-0.5)*int(numtravelers)
        ycafare = db.execute("SELECT YCA_FARE FROM CityPair WHERE airfare= ?", airfare2)
        airfare = 0 + float(ycafare[0]["YCA_FARE"])*2*int(numtravelers)
        pov = float(request.form.get("pov"))*0.67*int(numtravelers)
        misc = float(request.form.get("misc"))*int(numtravelers)
        total = (lodging + mie + airfare + pov + misc)
        # Insert into database
        db.execute("INSERT INTO trips (id,tripname,numtravelers,startdate,enddate,datediff,location,lodging,perdiem,airfare,ycafare,pov,misc,total) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       session["user_id"],tripname,int(numtravelers),startdate,enddate,datediff,location,lodging,mie,airfare2,airfare,pov,misc ,total)
        airfarelookup = db.execute("SELECT DISTINCT AIRFARE FROM CityPair")
        tripdata = db.execute("SELECT DISTINCT * FROM trips WHERE id =? AND tripname = ?", session["user_id"], tripname)
        lodgpernight='$'+str((tripdata[0]["lodging"]/(tripdata[0]["datediff"]-1))/tripdata[0]["numtravelers"])+'/night'
        miepernight='$'+str((tripdata[0]["perdiem"]/(tripdata[0]["datediff"]-0.5))/tripdata[0]["numtravelers"])+'/day'
        return render_template("trips.html",tripname=tripname,tripdata=tripdata,lodgpernight=lodgpernight,miepernight=miepernight,airfarelookup=airfarelookup,location=location)
    else:
        return render_template("createtrips.html")

@app.route("/addtraveler", methods=["POST"])
@login_required
def addtraveler():
    """Add Travelers"""
    tripname = request.form.get("tripname")
    numtravelers = request.form.get("numtravelers")
    airfare2 = request.form.get("airfarelookup")
    data = db.execute("SELECT DISTINCT * FROM trips WHERE id =? AND tripname = ?", session["user_id"], tripname)
    lodging = float((data[0]["lodging"]/(data[0]["datediff"]-1))/data[0]["numtravelers"])*int(numtravelers)*(data[0]["datediff"]-1)
    mie = float((data[0]["perdiem"]/(data[0]["datediff"]-0.5))/data[0]["numtravelers"])*int(numtravelers)*(data[0]["datediff"]-0.5)
    ycafare = db.execute("SELECT YCA_FARE FROM CityPair WHERE airfare= ?", airfare2)
    airfare = 0 + float(ycafare[0]["YCA_FARE"])*2*int(numtravelers)
    pov = float(request.form.get("pov"))*0.67*int(numtravelers)
    misc = float(request.form.get("misc"))*int(numtravelers)
    total = (lodging + mie + airfare + pov + misc)
    db.execute("INSERT INTO trips (id,tripname,numtravelers,startdate,enddate,datediff,location,lodging,perdiem,airfare,ycafare,pov,misc,total) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       session["user_id"],tripname,int(numtravelers),data[0]["startdate"],data[0]["enddate"],data[0]["datediff"],data[0]["location"],lodging,mie,airfare2,airfare,pov,misc ,total)

    tripdata = db.execute("SELECT DISTINCT * FROM trips WHERE id =? AND tripname = ?", session["user_id"], tripname)
    lodgpernight='$'+str((tripdata[0]["lodging"]/(tripdata[0]["datediff"]-1))/tripdata[0]["numtravelers"])+'/night'
    miepernight='$'+str((tripdata[0]["perdiem"]/(tripdata[0]["datediff"]-0.5))/tripdata[0]["numtravelers"])+'/day'
    location=data[0]["location"]
    airfarelookup = db.execute("SELECT DISTINCT AIRFARE FROM CityPair")
    return render_template("trips.html",tripname=tripname,location=location,tripdata=tripdata,lodgpernight=lodgpernight, miepernight=miepernight, airfarelookup=airfarelookup)

@app.route("/pasttrips", methods=["GET","POST"])
@login_required
def pasttrips():
    """Past Trip"""
    if request.method == "GET":
        tripname = db.execute("SELECT DISTINCT tripname FROM trips WHERE id =?", session["user_id"])
        return render_template("past_trips.html",tripname=tripname)
    else:
        tripname = request.form.get("tripname")
        tripdata = db.execute("SELECT * FROM trips WHERE id =? AND tripname = ?", session["user_id"], tripname)
        lodgpernight='$'+str((tripdata[0]["lodging"]/(tripdata[0]["datediff"]-1))/tripdata[0]["numtravelers"])+'/night'
        miepernight='$'+str((tripdata[0]["perdiem"]/(tripdata[0]["datediff"]-0.5))/tripdata[0]["numtravelers"])+'/day'
        location=tripdata[0]["location"]
        tripname = db.execute("SELECT DISTINCT tripname FROM trips WHERE id =?", session["user_id"])
        return render_template("past_trips.html", tripdata=tripdata, location=location,lodgpernight=lodgpernight,miepernight=miepernight,tripname=tripname )

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["ID"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        password = generate_password_hash(request.form.get("password"))

        if not request.form.get("username"):
            return apology("must provide username", 400)
        elif not request.form.get("password"):
            return apology("must provide password", 400)
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords must match", 400)

          # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        if len(rows) > 0:
            return apology("username already taken", 400)
        else:
            db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, password)

        rows2 = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        session["user_id"] = rows2[0]["ID"]
        return redirect("/")
    else:
        return render_template("register.html")
