from flask import Flask, render_template, request, redirect, url_for, \
    jsonify, make_response, flash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Items, User

from flask import session as login_session
import random
import string

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
import requests

CLIENT_ID = json.loads(open(
    'client_secret.json', 'r').read())['web']['client_id']

app = Flask(__name__)

engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.bind = create_engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


####################
# Helper Functions #
####################

# Create a new user from google info
def createUser(login_session):
    newUser = User(userName=login_session['username'],
                   userEmail=login_session['email'],
                   userPicture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(
        userEmail=login_session['email']).first()
    return user.userId


# Returns user info based off userId
def getUserInfo(user_id):
    user = session.query(User).filter_by(userId=user_id).first()
    return user


# Uses email to determine userID, if exists
def getUserID(email):
    try:
        user = session.query(User).filter_by(userEmail=email).first()
        return user.userId
    except:
        return None


# Determine if a user exists or not
def userExists():
    email = login_session['email']
    return session.query(User).filter_by(userEmail=email).one_or_none()


# Redirect if access denied
def loginRedirect():
    if 'username' not in login_session:
        return redirect('/catalog/login')


##############
# App Routes #
##############

# Home page will display categories and top 3 latest items added
@app.route('/')
@app.route('/catalog')
def showCatalog():
    users = session.query(User).all()
    for i in users:
        print i.userId, i.userName, i.userEmail
    categories = session.query(Category)
    items = session.query(Items).order_by(Items.createdDate.desc()).limit(3)
    return render_template('landing.html', categories=categories, items=items)


# State token login
@app.route('/catalog/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    categories = session.query(Category)
    return render_template('login.html', STATE=state, categories=categories)


# Connecting to google accounts
@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secret.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps(
                                 'Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    user_id = getUserID(data['email'])
    if not userExists():
	    user_id = createUser(login_session)
    login_session['user_id'] = user_id

    return "Login successul."


# Disconnect from google account
@app.route('/catalog/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')
    if access_token is None:
        print 'Access Token is None'
        response = make_response(json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    print 'In gdisconnect access token is %s', access_token
    print 'User name is: '
    print login_session['username']
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % login_session['access_token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'result is '
    print result
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# Add a category
@app.route('/catalog/newCategory', methods=['GET', 'POST'])
def newCategory():
    if 'username' not in login_session:
        return redirect('/catalog/login')
    if request.method == 'POST':
        newCategory = Category(categoryDesc=request.form['name'],
                               userId=login_session['user_id'])
        session.add(newCategory)
        session.commit()
        return redirect(url_for('showCatalog'))
    else:
        categories = session.query(Category)
        return render_template('newCategory.html', categories=categories)


# Descripton of item
@app.route('/catalog/<int:categoryId>/<int:itemId>')
def showItem(categoryId, itemId):
    item = session.query(Items).filter_by(itemId=itemId)
    category = session.query(Category).filter_by(categoryId=categoryId)
    categories = session.query(Category)
    return render_template('singleItem.html', item=item, category=category,
                           categories=categories)


# Single Category
@app.route('/catalog/<int:categoryId>')
def showCategory(categoryId):
    category = session.query(Category).filter_by(categoryId=categoryId)
    categories = session.query(Category)
    items = session.query(Items).filter_by(categoryId=categoryId)
    countItems = session.query(Items).filter_by(categoryId=categoryId).count()
    return render_template('singleCategory.html', category=category,
                           categories=categories, items=items,
                           count=countItems)


# Edit a category
@app.route('/catalog/<int:categoryId>/Edit', methods=['GET', 'POST'])
def editCategory(categoryId):
    if 'username' not in login_session:
        return redirect('/catalog/login')
    editedCategory = session.query(Category).filter_by(
        categoryId=categoryId).one()
    creator = getUserInfo(editedCategory.userId)
    if creator.userId != login_session['user_id']:
        return redirect('/catalog/login')
    if request.method == 'POST':
        if request.form['Id']:
            editedCategory.categoryDesc = request.form['Id']
            session.add(editedCategory)
            session.commit()
            return redirect(url_for('showCatalog'))
    else:
        categories = session.query(Category)
        return render_template('editCategory.html', categoryId=categoryId,
                               i=editedCategory, categories=categories)


# Delete a category
@app.route('/catalog/<int:categoryId>/Delete', methods=['GET', 'POST'])
def deleteCategory(categoryId):
    if 'username' not in login_session:
        return redirect('/catalog/login')
    deleteCategory = session.query(Category).filter_by(
        categoryId=categoryId).one()
    creator = getUserInfo(deleteCategory.userId)
    if creator.userId != login_session['user_id']:
        return redirect('/catalog/login')
    if request.method == 'POST':
        session.delete(deleteCategory)
        session.commit()
        return redirect(url_for('showCatalog'))
    else:
        categories = session.query(Category)
        return render_template('deleteCategory.html', categoryId=categoryId,
                               i=deleteCategory, categories=categories)


# Add an item
@app.route('/catalog/<int:categoryId>/newItem', methods=['GET', 'POST'])
def newItem(categoryId):
    if 'username' not in login_session:
        return redirect('/catalog/login')
    category = session.query(Category).filter_by(categoryId=categoryId).one()
    if request.method == 'POST':
        newItem = Items(itemName=request.form['name'],
                        itemDesc=request.form['description'],
                        categoryId=categoryId,
                        userId=login_session['user_id'])
        session.add(newItem)
        session.commit()
        return redirect(url_for('showCategory', categoryId=categoryId))
    else:
        categories = session.query(Category)
        return render_template('newItem.html', categories=categories,
                               i=category)


# Edit an item
@app.route('/catalog/<int:categoryId>/<int:itemId>/Edit',
           methods=['GET', 'POST'])
def editItem(categoryId, itemId):
    if 'username' not in login_session:
        return redirect('/catalog/login')
    editedItem = session.query(Items).filter_by(itemId=itemId).one()
    creator = getUserInfo(editedItem.userId)
    if creator.userId != login_session['user_id']:
        return redirect('/catalog/login')
    if request.method == 'POST':
        editedItem.itemName = request.form['name']
        editedItem.itemDesc = request.form['description']
        session.add(editedItem)
        session.commit()
        return redirect(url_for('showCategory', categoryId=categoryId))
    else:
        categories = session.query(Category)
        return render_template('editItem.html', categories=categories,
                               i=editedItem)


# Delete an item
@app.route('/catalog/<int:categoryId>/<int:itemId>/Delete',
           methods=['GET', 'POST'])
def deleteItem(categoryId, itemId):
    if 'username' not in login_session:
        return redirect('/catalog/login')
    deleteItem = session.query(Items).filter_by(itemId=itemId).one()
    creator = getUserInfo(deleteItem.userId)
    if creator.userId != login_session['user_id']:
        return redirect('/catalog/login')
    if request.method == 'POST':
        session.delete(deleteItem)
        session.commit()
        return redirect(url_for('showCategory', categoryId=categoryId))
    else:
        categories = session.query(Category)
        return render_template('deleteItem.html', categories=categories,
                               i=deleteItem)

###############
# JSON Routes #
###############

@app.route('/catalog/JSON')
def calaogJSON():
    category = session.query(Category).all()
    items = session.query(Items).all()
    return jsonify(Category=[i.serialize for i in category],
                   Items=[j.serialize for j in items])


@app.route('/catalog/<int:categoryId>/<int:itemId>/JSON')
def itemJSON(categoryId, itemId):
    item = session.query(Items).filter_by(itemId=itemId)
    return jsonify(Items=[i.serialize for i in item])


####################
# Always important #
####################

if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
