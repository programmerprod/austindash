from flask import url_for, render_template, redirect, flash, jsonify, json, request
from sqlalchemy import desc
from austinpos import app, db, bcrypt, mail, socketio, emit
from austinpos.forms import LoginForm, RegistrationForm, CrazyForm, SubmitForm, AddSiteForm, MessageForm, QuestionForm
from austinpos.models import Users, Rma, OrderCart, Sites, FaQuestion, Messages, Ticket
from flask_login import login_user, current_user, logout_user, login_required
import requests, json
from flask_mail import Message

cart = {}

equipment = {
    'Loaner Terminal': '150',
    'Loaner Thermal Printer': '85',
    'Loaner MSR': '50',
    'Loaner Kitchen Printer': '85',
    'Loaner Desktop PC': '150',
    'Loaner Cash Drawer':'50',
    'Thermal Printer':'350',
    'Kitchen Printer':'385',
    'MSR':'150',
    'Cash Drawer': '150',
    'Parallel Cable':'12.95',
    'Serial Cable':'12.95',
    'Cash Drawer Cable':'12.95',
    'Punch Downs':'5.95',
    'New Line': '150',
    'Terminal Power Supply':'150',
    'Printer Power Supply':'75',
    'Used Printer Power Supply':'37.50',
    'Used Terminal Power Supply': '75',
    'Used MSR': '75',
    'SSD 120GB': '99'
}


# ------------------- SITE LOGIN -------------------------------------------------
@app.route('/', methods=['POST', 'GET'])
def login():
    db.create_all()
    if current_user.is_authenticated:
        return redirect(url_for('dash'))
    form = LoginForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            flash(f'Welcome {current_user.username}!')
            return redirect(url_for('dash'))
        else:
            flash('Login unsuccessful. Please check email and password.')
    return render_template('login.html', name = 'login', form=form)

# ----------------------------- SITE'S DASHBOARD -----------------------------
@app.route("/Dash", methods=['GET', 'POST'])
@login_required
def dash():
    db.create_all()
    return render_template('dash.html')


# ADD REQUEST SID TO USER IN DB
@socketio.on('connected')
def handle_my_custom_event(json):
    endusers = Users.query.filter_by(username = current_user.username).first()
    print('this user ', endusers)
    endusers.sid = request.sid
    db.session.commit()


# SUBMITTED TICKET FROM USER ADD TICKET ID TO DB, NEED TO ADD MORE INFO ON TICKET SUCH AS USER, AND MESSAGE FOR HISTORY
# SEND TO PRIVATE ADMIN TICKETS IN MESSAGEBOX.JS
@socketio.on('adminticketblast')
def adminticketblast(data):
    db.session.add(Ticket(site = data['site'], user = data['username'], issue = data['type'], message = data['message']))
    db.session.commit()
    ticket = str(Ticket.query.order_by(Ticket.id.desc()).first().id)
    socketio.emit('privateadmintickets', (data, ticket) , broadcast=True)

@socketio.on('adminselected')
def adminselected(data):
    print(data)
    socketio.emit('selected_confirmed', data, broadcast=True)

@socketio.on('displaymessage')
def displaymessage(data):
    if data['admin'] == current_user.username:
        print(data['adminsmess']['message'])
        print(current_user.username, current_user.sid)
        print(Users.query.filter_by(username=data['admin']).first().sid)
        socketio.emit('showadminmessage', data, room=Users.query.filter_by(username=data['admin']).first().sid)
    else:
        print('Not your message')


@socketio.on('messagestream')
def messagestream(data):
    roomid = Users.query.filter_by(username = data['recipient']).first().sid
    
    
    userrecipient = Ticket.query.filter_by(user = data['recipient']).first()
    print(userrecipient)
    if userrecipient is None:
        userrecipient.recipient = data['username']
        db.session.commit()
    else:
        site_ = Ticket.query.filter_by(user = data['recipient']).first().site
        ticket = Ticket.query.filter_by(user = data['recipient']).first().issue
        
        db.session.add(Ticket(site = site_, user = data['username'], issue = ticket, message = data['message'], recipient = data['recipient']))
        db.session.commit()
    print('messagestream', data)
    socketio.emit('playerroom', data, room=roomid)
    

# --------------------- LOGOUT USER ----------------------
@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('login'))

# --------------------- REGISTER NEW USER ------------------------------------------------------
@app.route('/register', methods=['POST', 'GET'])
# @login_required
def register():
    db.create_all()
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_pw = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        print(form.site.data)
        siteid = Sites.query.filter_by(sitename=form.site.data.sitename).first().id
        user = Users(site = form.site.data.sitename, username = form.username.data, email = form.email.data, 
        password = hashed_pw, adminstatus= form.admin_status.data, sitelink=siteid)
        db.create_all()
        db.session.add(user)
        db.session.commit()
        flash(f"{form.username.data} has been added!")
        return redirect(url_for('dash'))

    return render_template('register.html', name = 'login', form=form)

# ----------------------------------- CREATE AN RMA ---------------------------------------------- 
@app.route('/rma/create-rma', methods=['POST', 'GET'])
@login_required
def createrma():
    form2 = CrazyForm()
    if form2.validate_on_submit():
        rma = Rma(site=form2.Site.data.sitename, serialnumber=form2.serialnumber.data, rmanumber=form2.RmaNumber.data, Vendor=form2.Vendor.data,
            Issue=form2.Issue.data, Date_Sent=form2.Date_Sent.data.strftime('%Y-%m-%d'), Date_Received=form2.Date_Received.data.strftime('%Y-%m-%d'),
            Rep=form2.Rep.data, Notes=form2.Notes.data)
        db.session.add(rma)
        db.session.commit()
        return redirect(url_for('rma'))
    else:
        print('Invalid submission')
    return render_template('create-rma.html', name = 'createrma_', form=form2)

# --------------------------------- VIEW SITE'S RMA'S ----------------------------------
@app.route('/rma', methods=['GET', 'POST'])
@login_required
def rma():
    rmas = Rma.query.all()
    return render_template('rma.html', name = 'rma', info=rmas)

# ------------------------------- PRICING --------------------------------
@app.route('/pricing', methods=['POST', 'GET'])
@login_required
def pricing():
    orders = SubmitForm()
    price_info = equipment
    return render_template('pricing.html', pricing = price_info, orders = orders)

# ----------------------------------- PAYMENT PAGE -----------------------------------
@app.route('/pricing/orders')
@login_required
def Order():
    return render_template('Order.html', name='order')

# ---------------------------------- USER CART API -----------------------------
@app.route('/pricing/orders/<user_name>/api', methods=['POST', 'GET'])
@login_required
def api(user_name):
    user_name = current_user.username
    if request.method == 'POST':
        usersItem = json.loads(request.form["javascript_data"])
        if user_name in cart:
            cart[user_name].append(usersItem)
        else:
            cart[user_name] = [usersItem]
        print(cart[user_name])
    return jsonify(cart[user_name])

# ---------------------------- DELETE ITEM IN CART ROUTE ----------------------------------
@app.route('/pricing/orders/<user_name>/delete', methods=['POST', 'GET'])
@login_required
def delete_item(user_name):
    user_name = current_user.username
    print(user_name)
    if request.method == 'POST':
        if user_name in cart:
            deleteItem = json.loads(request.form["delete_item"])
            cart[user_name].pop(deleteItem)
            print(cart[str(user_name)])
    return jsonify({"whoa": "there"})

# ----------------------------- DISPLAY CART BADGE LENGTH---------------------------------
@app.context_processor
def inject_badge_length():
    badge_length=0
    for x,y in cart.items():
        if current_user.is_authenticated:
            for z in cart.keys():
                if z == current_user.username:
                    print(z)
                    badge_length=len(y)
                    print(len(y))
    return {'BADGE_LENGTH' : badge_length}

# ------------------------------- ADD SITE -----------------------------------------
@app.route('/sites/addsite', methods=['POST', 'GET'])
# @login_required
def addsites():
    form = AddSiteForm()
    print(form.sitename.data)
    if form.validate_on_submit():
        newsite = Sites(sitename=form.sitename.data, contractstart=form.contractstart.data.strftime('%Y-%m-%d'), contractend=form.contractend.data.strftime('%Y-%m-%d'), 
        hwkey=form.hwkey.data, stations=str(form.stations.data), printers=str(form.printers.data), remprinters=str(form.remprinters.data), 
        bof=form.bof.data, processor=str(form.processor.data), giftopt=str(form.giftopt.data))
        db.session.add(newsite)
        db.session.commit()
        flash(f'{form.sitename.data} has been added to the database')
        return redirect(url_for('sites'))
    else:
        print('Invalid submission')
    return render_template('addsites.html', form = form)

# -------------------------- ADMIN VIEW SITES ---------------------------------
@app.route('/sites', methods=['POST','GET']) 
@login_required
def sites():
    form = MessageForm()
    sites = Sites.query.all()
    if form.validate_on_submit():
        msg = Message("Austin Dash Confirmation Message",
                        sender="service@gmail.com")
        msg.recipients = ["andrew@austintxpos.com"]
        msg.body = form.message.data
        mail.send(msg)
        print("Message Sent")
    else:
        print("Message did not send")
    return render_template('sites.html', sites=sites, form=form)

# ---------------------------------- SITE INFO -----------------------------------------
@app.route('/siteinfo', methods=['POST', 'GET'])
@login_required
def siteinfo():
    if current_user.adminstatus == True:
        form = MessageForm()
        sites = Sites.query.all()
        x = request.form.get('sitesss')
        userinfo = Users.query.filter_by(site=x).all()
        if form.validate_on_submit():
            if form.emailtype.data=="Mass Message":
                massmail = Users.query.all()
                msg = Message("Austin Pos Alert",
                                sender="service@gmail.com")
                msg.bcc = []
                #Get all users emails
                for user in massmail:
                    msg.bcc.append(user.email)
                msg.body = form.message.data
                mail.send(msg)
                print("Mass message sent")
            else:
                sitemail = Users.query.filter_by(site=form.sitename.data)
                msg = Message("Austin Pos Message",
                                sender="service@gmail.com")
                msg.recipients = []
                #Get Specified sites user emails
                for user in sitemail:
                    msg.recipients.append(user.email)
                    print("Message sent to", user.username)
                msg.body = form.message.data
                mail.send(msg)
        else:
            print("Message did not send")
        return render_template('sites.html', x=x, sites=sites, form=form, userinfo=userinfo)
    else:
        return 'Invalid Request'

# ---------------------------FAQS----------------------------------------
@app.route('/AustinPos/Resources/FAQs', methods=['POST', 'GET'])
@login_required
def faqs():
    form = QuestionForm()
    questions = FaQuestion.query.all()
    if form.validate_on_submit():
        print("why is this running")
        question = FaQuestion(Type=form.Type.data, Question=form.Question.data)
        db.session.add(question)
        db.session.commit()
        flash("Question added.")
        return redirect(url_for("faqs"))
    return render_template('faqs.html', form=form, questions = questions)

@app.route('/AustinPos/Resources/FAQs/Printers', methods=['GET', 'POST'])
@login_required
def faqsPrinters():
    form=QuestionForm()
    questions=FaQuestion.query.all()
    if form.validate_on_submit():
        print("why is this running")
        question = FaQuestion(Type=form.Type.data, Question=form.Question.data)
        db.session.add(question)
        db.session.commit()
        flash("Question added.")
        return redirect(url_for("faqs"))
    return render_template('printersquestions.html',form=form, questions = questions)

@app.route('/AustinPos/Resources/FAQs/Terminals', methods=['GET', 'POST'])
@login_required
def faqsTerminals():
    form=QuestionForm()
    questions=FaQuestion.query.all()
    if form.validate_on_submit():
        print("why is this running")
        question = FaQuestion(Type=form.Type.data, Question=form.Question.data)
        db.session.add(question)
        db.session.commit()
        flash("Question added.")
        return redirect(url_for("faqs"))
    return render_template('terminalsquestions.html',form=form, questions = questions)

@app.route('/AustinPos/Resources/FAQs/Logmein', methods=['GET', 'POST'])
@login_required
def faqsLogmein():
    form=QuestionForm()
    questions=FaQuestion.query.all()
    if form.validate_on_submit():
        print("why is this running")
        question = FaQuestion(Type=form.Type.data, Question=form.Question.data)
        db.session.add(question)
        db.session.commit()
        flash("Question added.")
        return redirect(url_for("faqs"))
    return render_template('logmeinquestions.html',form=form, questions = questions)

@app.route('/AustinPos/Resources/FAQs/Giftcards', methods=['GET', 'POST'])
@login_required
def faqsGiftcards():
    form=QuestionForm()
    questions=FaQuestion.query.all()
    if form.validate_on_submit():
        print("why is this running")
        question = FaQuestion(Type=form.Type.data, Question=form.Question.data)
        db.session.add(question)
        db.session.commit()
        flash("Question added.")
        return redirect(url_for("faqs"))
    return render_template('giftcardsquestions.html',form=form, questions = questions)

@app.route('/AustinPos/Resources/FAQs/Networking', methods=['GET', 'POST'])
@login_required
def faqsNetworking():
    form=QuestionForm()
    questions=FaQuestion.query.all()
    if form.validate_on_submit():
        print("why is this running")
        question = FaQuestion(Type=form.Type.data, Question=form.Question.data)
        db.session.add(question)
        db.session.commit()
        flash("Question added.")
        return redirect(url_for("faqs"))
    return render_template('networkingquestions.html',form=form, questions = questions)

@app.route('/AustinPos/Resources/FAQs/Emv', methods=['GET', 'POST'])
@login_required
def faqsEmv():
    form=QuestionForm()
    questions=FaQuestion.query.all()
    if form.validate_on_submit():
        print("why is this running")
        question = FaQuestion(Type=form.Type.data, Question=form.Question.data)
        db.session.add(question)
        db.session.commit()
        flash("Question added.")
        return redirect(url_for("faqs"))
    return render_template('emvquestions.html',form=form, questions = questions)

#---------------------CONTACT PAGE---------------------------------------------------
@app.route('/AustinPos/contact', methods=['POST', 'GET'])
@login_required
def contact():
    return render_template('contact.html')

