import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd
from datetime import datetime
import time
import math
# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    portfolio = db.execute("SELECT symbol, SUM(quantity) FROM transactions WHERE user_id = :user_id GROUP BY symbol", user_id = session["user_id"])
    
    h = []
    y = 0
    for x in portfolio:
        h.append(lookup(portfolio[y].get('symbol')))
        time.sleep(0.2)
        y += 1
    l = []
    u = 0    
    for x in h:    
        l.append(usd(h[u].get('price')))
        u += 1
    
    f = []
    m = 0
    for x in h:
        price = float(h[m].get('price'))
        shares = int(portfolio[m].get('SUM(quantity)'))
        total = shares * price
        r = usd(total)
        f.append(r)        
        m += 1
        
    #shares cash
    sc = 0
    c = 0
    for x in portfolio:
        quantity = portfolio[c].get('SUM(quantity)')
        price = h[c]['price']
        value = quantity * price
        sc += value
        
        c += 1
        
    cash = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id = session['user_id'])
    gt = float(cash[0].get('cash')) + float(sc)
    sc = usd(sc)
    cash = usd(cash[0].get('cash'))
    
    return render_template('index.html', portfolio = portfolio , l = l, f = f, quote = h, cash = cash, sc = sc,gt = gt)


@app.route("/add_cash", methods=["GET","POST"])
@login_required
def add_cash():
    if request.method == "POST":
        transfer = round(float(request.form.get('cash')),2)
        cc = round(float(db.execute("SELECT cash FROM users WHERE id = :user_id", user_id = session["user_id"])[0].get('cash')),2)
        
        cash = cc + transfer
        add_cash = db.execute("UPDATE users set cash = :cash WHERE id = :user_id",user_id = session["user_id"], cash = cash)
        flash(f'Your cash is ${cash}')
        return redirect('/')
    else:
        return render_template("add_cash.html")

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        
        symbol = request.form.get('symbol').upper()        
        if not symbol:
            return apology('put in a symbol',400)
        
        quote = lookup(symbol)
        if not quote:
            return apology('type better',400)
        
        try:
            if int(request.form.get('shares')) < 1:
                return apology('how many shares?', 400)
        except:
            return apology('invalid input for shares', 400)
        
        nr_of_shares = int(request.form.get('shares'))
        if nr_of_shares == '0':
            return apology('you wanna buy 0 shares??',400)
        
        if not nr_of_shares:
            return apology('how many shares??',400)
        
        if quote:
            price = quote.get('price')
            total = int(nr_of_shares) * float(price) 
            round(total , 2)
            # users current cash db.execute returns a list with a dict 
            sqldict = db.execute('SELECT cash FROM users WHERE id = :user_id' , user_id = session["user_id"])
            # getting the cash value from the dict and turning it into a float
            cc = float(sqldict[0].get('cash'))
            date = datetime.now().strftime("%x")
            time = datetime.now().strftime("%X")
            if total > cc:
                return apology('you are poor',400)
            else:
                cc -= total
            
                db.execute("UPDATE USERS SET cash  = :cc WHERE id = :user_id", cc = cc, user_id = session['user_id'])                  
                db.execute("INSERT INTO transactions (user_id, symbol, quantity, price, total, date, time) VALUES(:user_id, :symbol, :shares, :price,  :total,                 :date, :time)",
                user_id = session['user_id'], symbol = symbol, shares = nr_of_shares, price = price, total = total, date = date, time = time)
                flash('Shares bought')
                return redirect ('/')
        
        
        
        if not quote:
            return apology('type better')
        
        
    else:
        return render_template('buy.html')
        
    




@app.route("/check", methods=["GET"])
def check():
    """Return true if username available, else false, in JSON format"""
    username = request.args.get('username')
    if username:
        
        old_user = db.execute("SELECT username FROM users WHERE username = :username", username = username)
    
        if len(old_user) > 0:
            return jsonify(False)
        else:
            return jsonify(True)
    
    


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    transaction = db.execute("SELECT * FROM transactions WHERE user_id = :user_id", user_id = session["user_id"])
    name = []
    y = 0
    for x in transaction:
        name.append(lookup(transaction[y].get('symbol')))
        y += 1
    return render_template('history.html', transaction = transaction, name = name)
    
    


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
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

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


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        symbol = request.form.get('symbol')
        quote = lookup(symbol)
        if not symbol:
            return apology('yo put in a symbol')
        
        elif not quote:
            return apology ('not valid symbol')
        price = usd(quote.get('price'))
        return render_template('quoted.html', name = quote.get('name'), symbol = quote.get('symbol'), price = price)
    
    else:
        return render_template('quote.html')
    
    


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if  request.method == "POST":
        
        
        if not request.form.get('username') and not request.form.get('password'):
            return apology("dude you've got to provide Usern and Passw")
        
        elif not request.form.get('username'):
            return apology('no usern')
        
        elif not request.form.get('password'):
            return apology('no passw')
        
        elif request.form.get('password') != request.form.get('confirmation'):
            return apology('yo the passwordsd do not match')
        
        
        username = db.execute('SELECT username FROM users WHERE username = :username', username = request.form.get('username'))
        
        if len(username) > 0:
            return apology('username taken')
         
        
        hash = generate_password_hash(request.form.get('password'))
        client = db.execute("INSERT INTO users ('username', 'hash') VALUES (:username ,:hash)", username =                                                             request.form.get('username'), hash = hash)
        
        session['user_id'] = client
        flash('You are registered')
        
        
    else:
        old_user = db.execute("SELECT username FROM users WHERE username = :new_user", new_user = 'sullabanda')
        return render_template('register.html', old_user = old_user)
    
    return redirect ('/')    
    
    


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    portfolio = db.execute("SELECT quantity, symbol FROM transactions WHERE user_id = :user_id GROUP BY symbol", user_id = session["user_id"])
    
    if request.method == "POST":
        symbol = request.form.get('symbol')
        if not symbol:
            return apology('no symbol')
               
        shares = request.form.get('shares')
        if not shares:
            return apology('no number of shares')
        
        shares = int(shares)
        # number of shares owned
        noso = db.execute("SELECT SUM(quantity) FROM transactions WHERE user_id = :user_id AND symbol = :symbol",user_id = session["user_id"], symbol = symbol)
        
        if shares > noso[0].get("SUM(quantity)"):
            return apology('yeah you wish')
        # current price = cp, total price of number of shares
        cp = float(lookup(symbol).get('price'))        
        total = round((shares * cp),2)
        # convert shares to negative number,because they were sold
        shares = shares *  (-1)
        date = datetime.now().strftime("%x")
        time = datetime.now().strftime("%X")
        
        database_insert_transactions = db.execute("INSERT INTO transactions(user_id, symbol, quantity, price, total, date, time) VALUES(:user_id, :symbol,             :shares, :cp, :total, :date, :time)",user_id = session["user_id"], symbol = symbol, shares = shares, cp = cp, total = total, date = date, time = time)
        
        
        user_cash = db.execute("SELECT cash FROM users WHERE id =:user_id",user_id = session["user_id"])
        fc = float(user_cash[0].get('cash'))
        fc += total
        round(fc, 2)                 
        update_cash = db.execute("UPDATE users SET cash = :user_cash WHERE id = :user_id", user_cash = fc, user_id = session["user_id"])                  
        flash(f'sold...for ${total}')
        
        return redirect('/')
        
        
            
    
    else:
        return render_template('sell.html', portfolio = portfolio)
    


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
