from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask_login import current_user
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, IntegerField, DateField, \
    SelectField, HiddenField, RadioField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Regexp
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from ecommerce import db
from ecommerce.models import *
from wtforms.fields.html5 import DateField
import os
import secrets
from PIL import Image
from flask import render_template, url_for, flash, redirect, request, abort
from ecommerce.models import *
from sqlalchemy import select, func, Integer, Table, Column, MetaData
from flask import session, request
import hashlib, os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText




def getAllProducts():
    itemData = Product.query.with_entities(Product.productid, Product.product_name, Product.regular_price,
                                           Product.description, Product.image, Product.quantity).all()
    return itemData


def getAllCategoryId():
    return Category.query.with_entities(Category.categoryid, Category.category_name).all()


def massageItemData(data):
    ans = []
    i = 0
    while i < len(data):
        curr = []
        for j in range(6):
            if i >= len(data):
                break
            curr.append(data[i])
            i += 1
        ans.append(curr)
    return ans


def is_valid(email, password):
    data = User.query.with_entities(User.email, User.password).all()
    for row in data:
        if row[0] == email and row[1] == hashlib.md5(password.encode()).hexdigest():
            return True
    return False


def getLoginUserDetails():
    productCountinCartForGivenUser = 0

    if 'email' not in session:
        loggedIn = False
        firstName = ''
    else:
        loggedIn = True
        userid, firstName = User.query.with_entities(User.userid, User.fname).filter(
            User.email == session['email']).first()

        productCountinCart = []

        # for Cart in Cart.query.filter(Cart.userId == userId).distinct(Products.productId):
        for cart in Cart.query.filter(Cart.userid == userid).all():
            productCountinCart.append(cart.productid)
            productCountinCartForGivenUser = len(productCountinCart)

    return (loggedIn, firstName, productCountinCartForGivenUser)


def getProductDetails(productId):
    productDetailsById = Product.query.filter(Product.productid == productId).first()
    return productDetailsById


def extractAndPersistUserDataFromForm(request):
    password = request.form['password']
    email = request.form['email']
    firstName = request.form['firstName']
    lastName = request.form['lastName']
    address1 = request.form['address1']
    address2 = request.form['address2']
    zipcode = request.form['zipcode']
    city = request.form['city']
    state = request.form['state']
    country = request.form['country']
    phone = request.form['phone']

    user = User(fname=firstName, lname=lastName, password=hashlib.md5(password.encode()).hexdigest(), address1=address1,
                address2=address2,
                city=city, state=state, country=country, zipcode=zipcode, email=email, phone=phone)
    db.session.add(user)
    db.session.flush()
    db.session.commit()
    return "Registered Successfully"


def isUserLoggedIn():
    if 'email' not in session:
        return False
    else:
        return True


def extractAndPersistKartDetails(productId):
    userId = User.query.with_entities(User.userid).filter(User.email == session['email']).first()
    userId = userId[0]
    kwargs = {'userid': userId, 'productid': productId}
    quantity = Cart.query.with_entities(Cart.quantity).filter_by(**kwargs).first()

    if quantity is not None:
        cart = Cart(userid=userId, productid=productId, quantity=quantity[0] + 1)
    else:
        cart = Cart(userid=userId, productid=productId, quantity=1)

    db.session.merge(cart)
    db.session.flush()
    db.session.commit()


class RegistrationForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is taken. Please choose a different one.')


class LoginForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

#START CART MODULE
#Gets products in the cart
def getusercartdetails():
    userId = User.query.with_entities(User.userid).filter(User.email == session['email']).first()

    productsincart = Product.query.join(Cart, Product.productid == Cart.productid) \
        .add_columns(Product.productid, Product.product_name, Product.discounted_price, Cart.quantity) \
        .add_columns(Product.discounted_price * Cart.quantity).filter(
        Cart.userid == userId)
    totalsum = 0

    for row in productsincart:
        totalsum += row[5]

    tax = ("%.2f" % (.06 * float(totalsum)))

    totalsum = float("%.2f" % (1.06 * float(totalsum)))
    return (productsincart, totalsum, tax)

#Removes products from cart when user clicks remove
def removeProductFromCart(productId):
    userId = User.query.with_entities(User.userid).filter(User.email == session['email']).first()
    userId = userId[0]
    kwargs = {'userid': userId, 'productid': productId}
    cart = Cart.query.filter_by(**kwargs).first()
    if productId is not None:
        db.session.delete(cart)
        db.session.commit()
        flash("Product has been removed from cart !!")
    else:
        flash("failed to remove Product cart please try again !!")
    return redirect(url_for('cart'))

#flask form for checkout details
class checkoutForm(FlaskForm):
    fullname = StringField('Full Name',
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    address = TextAreaField('address',
                            validators=[DataRequired()])
    city = StringField('city',
                       validators=[DataRequired(), Length(min=2, max=20)])
    state = StringField('state',
                        validators=[DataRequired(), Length(min=2, max=20)])
    zip = StringField('zip',
                      validators=[DataRequired(), Length(min=2, max=6)])
    cctype = RadioField('cardtype')
    cardname = StringField('cardnumber',
                           validators=[DataRequired(), Length(min=12, max=12)])
    ccnumber = StringField('Credit card number',
                           validators=[DataRequired()])

    expmonth = StringField('Exp Month',
                           validators=[DataRequired(), Length(min=12, max=12)])
    expyear = StringField('Expiry Year',
                          validators=[DataRequired(), Length(min=4, max=4)])
    cvv = StringField('CVV',
                      validators=[DataRequired(), Length(min=3, max=4)])
    submit = SubmitField('MAKE PAYMENT')

#Gets form data for the sales transaction

def extractOrderdetails(request, totalsum):
    fullname = request.form['FullName']
    email = request.form['email']
    address = request.form['address']
    phone=request.form['phone']
    city = request.form['city']
    state = request.form['state']
    zipcode = request.form['zip']
    cctype=request.form['cardtype']
    ccnumber = request.form['cardnumber']
    cardname = request.form['cardname']
    expmonth = request.form['expmonth']
    expyear = request.form['expyear']
    cvv = request.form['cvv']
    orderdate = datetime.utcnow()
    userId = User.query.with_entities(User.userid).filter(User.email == session['email']).first()
    userId = userId[0]
    order = Order(order_date=orderdate, total_price=totalsum, userid=userId)
    db.session.add(order)
    db.session.flush()
    db.session.commit()

    orderid = Order.query.with_entities(Order.orderid).filter(Order.userid == userId).order_by(Order.orderid.desc()).first()

    # add details to ordered;
    #  products table
    addOrderedproducts(userId,orderid)
    #add transaction details to the table
    updateSalestransaction(totalsum,ccnumber,orderid,cctype)

    #remove ordered products from cart after transaction is successful
    removeordprodfromcart(userId)
    #sendtextconfirmation(phone,fullname,orderid)
    return (email, fullname,orderid,address,fullname,phone)

# adds data to orderdproduct table

def addOrderedproducts(userId,orderid):

    cart=Cart.query.with_entities(Cart.productid,Cart.quantity).filter(Cart.userid == userId)

    for item in cart:
        orderedproduct=OrderedProduct(orderid=orderid, productid=item.productid, quantity=item.quantity)
        db.session.add(orderedproduct)
        db.session.flush()
        db.session.commit()

#removes all sold products from cart for the user

def removeordprodfromcart(userId):
    userid= userId
    db.session.query(Cart).filter(Cart.userid == userid).delete()
    db.session.commit()

#adds sales transaction

def updateSalestransaction(totalsum,ccnumber,orderid,cctype):
    salesTransaction = SaleTransaction(orderid=orderid, transaction_date=datetime.utcnow(), amount=totalsum,cc_number=ccnumber,cc_type=cctype,response="success")
    db.session.add(salesTransaction)
    db.session.flush()
    db.session.commit()

#sends email for order confirmation

def sendEmailconfirmation(email, username,ordernumber):
    msg = MIMEMultipart()
    sitemail = "stargadgets@engineer.com"
    msg['Subject'] = "Your Order has been placed for " + username
    msg['From'] = sitemail
    msg['To'] = email
    text = "Hello!\nThank you for shopping with us"
    html = """\
    <html>
      <head></head>
      <body>
        <p><br>
           Please stay tuned for more fabulous offers and gadgets.You can visit your account for more details on this order.<br> 
           <br>Please write to us at <u>shopoholic@usa.com</u> for any assistance.</br>
           <br></br>
           <br></br>
           Thank you!
           <br></br>
           Shopoholic Team          
        </p>
      </body>
    </html>
    """
    msg1 = MIMEText(text, 'plain')
    msg2 = MIMEText(html, 'html')
    msg.attach(msg1)
    msg.attach(msg2)
    server = smtplib.SMTP(host='smtp.mail.com', port=587)
    server.connect('smtp.mail.com', 587)
    # Extended Simple Mail Transfer Protocol (ESMTP) command sent by an email server to identify itself when connecting to another email.
    server.ehlo()
    #upgrade insecure connection to secure
    server.starttls()
    server.ehlo()
    server.login("stargadgets@engineer.com", "stargadget@123")
    server.ehlo()
    server.sendmail(sitemail, email, msg.as_string())
    server.quit()

#END CART MODULE