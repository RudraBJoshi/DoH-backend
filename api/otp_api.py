import random
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from flask_restful import Api, Resource
from model.user import User
import jwt as pyjwt
import os

otp_api = Blueprint('otp_api', __name__, url_prefix='/api')
api = Api(otp_api)

# In-memory OTP store: { email: {'otp': str, 'expires': datetime} }
_otp_store = {}


def _issue_jwt_response(user):
    """Build a response with a JWT cookie identical to the main authenticate endpoint."""
    token = pyjwt.encode(
        {"_uid": user._uid},
        current_app.config["SECRET_KEY"],
        algorithm="HS256"
    )
    resp = jsonify({
        "message": f"Authentication for {user._uid} successful",
        "user": {
            "uid": user._uid,
            "name": user.name,
            "role": user.role,
        }
    })
    is_prod = os.environ.get('IS_PRODUCTION', 'false').lower() == 'true'
    if is_prod:
        resp.set_cookie(
            current_app.config["JWT_TOKEN_NAME"], token,
            max_age=43200, secure=True, httponly=True,
            path='/', samesite='None', domain='.opencodingsociety.com'
        )
    else:
        resp.set_cookie(
            current_app.config["JWT_TOKEN_NAME"], token,
            max_age=43200, secure=False, httponly=False,
            path='/', samesite='Lax'
        )
    return resp


class OTPApi:

    class _Send(Resource):
        def post(self):
            body = request.get_json() or {}
            # Accept 'email' (login form) or 'uid' (API/legacy) as the identifier
            identifier = (body.get('email') or body.get('uid') or '').strip()
            password = body.get('password', '')

            if not identifier or not password:
                return {'message': 'Email/username and password are required'}, 400

            # Look up by email first, then fall back to uid
            user = User.query.filter_by(_email=identifier).first()
            if not user:
                user = User.query.filter_by(_uid=identifier).first()
            if not user or not user.is_password(password):
                return {'message': 'Invalid email/username or password'}, 401

            if not getattr(user, 'totp_enabled', True):
                return _issue_jwt_response(user)

            email = user._email
            # No email on file — skip OTP and issue JWT directly
            if not email or email == '?':
                return _issue_jwt_response(user)

            otp = str(random.randint(100000, 999999))
            _otp_store[email] = {
                'otp': otp,
                'expires': datetime.now() + timedelta(minutes=10)
            }

            smtp_user = os.environ.get('SMTP_USER')
            smtp_pass = os.environ.get('SMTP_PASSWORD')

            if not smtp_user or not smtp_pass:
                # Dev mode: print to console instead of sending
                print(f"[OTP DEV] Code for {email}: {otp}")
                return {'message': 'OTP printed to server console (SMTP not configured)', 'email': email}, 200

            try:
                msg = MIMEText(
                    f"Your login verification code is: {otp}\n\n"
                    f"This code expires in 10 minutes.\n"
                    f"If you did not request this, ignore this email."
                )
                msg['Subject'] = 'Your Login Code'
                msg['From'] = smtp_user
                msg['To'] = email
                with smtplib.SMTP('smtp.gmail.com', 587) as s:
                    s.starttls()
                    s.login(smtp_user, smtp_pass)
                    s.sendmail(smtp_user, email, msg.as_string())
            except Exception as e:
                return {'message': f'Failed to send email: {str(e)}'}, 500

            return {'message': 'Verification code sent to your email'}, 200

    class _Verify(Resource):
        def post(self):
            body = request.get_json() or {}
            # Accept 'email' (login form) or 'uid' (API/legacy)
            identifier = (body.get('email') or body.get('uid') or '').strip()
            otp = str(body.get('otp', '')).strip()

            if not identifier or not otp:
                return {'message': 'Email/username and code are required'}, 400

            # Look up by email first, then uid
            user = User.query.filter_by(_email=identifier).first()
            if not user:
                user = User.query.filter_by(_uid=identifier).first()
            if not user:
                return {'message': 'User not found'}, 404

            email = user._email
            if not email or email == '?':
                return {'message': 'No email address on file for this account'}, 400

            stored = _otp_store.get(email)
            if not stored:
                return {'message': 'No pending code for this account. Request a new one.'}, 400

            if datetime.now() > stored['expires']:
                _otp_store.pop(email, None)
                return {'message': 'Code expired. Request a new one.'}, 400

            if stored['otp'] != otp:
                return {'message': 'Invalid code'}, 401

            _otp_store.pop(email, None)
            return _issue_jwt_response(user)

    class _GoogleLogin(Resource):
        def post(self):
            body = request.get_json() or {}
            credential = body.get('credential', '')
            if not credential:
                return {'message': 'Google credential required'}, 400

            try:
                import base64, json as _json
                # Decode the Google JWT payload (Google already verified it on the client)
                padding = credential.split('.')[1]
                padding += '=' * (4 - len(padding) % 4)
                info = _json.loads(base64.urlsafe_b64decode(padding))
                email = info.get('email', '').strip().lower()
            except Exception:
                return {'message': 'Invalid Google credential'}, 400

            if not email:
                return {'message': 'Could not extract email from Google credential'}, 400

            user = User.query.filter_by(_email=email).first()
            if not user:
                return {
                    'message': 'No account found for this Google email. Please sign up first.',
                    'email': email
                }, 404

            return _issue_jwt_response(user)


    class _SignupSend(Resource):
        """Send OTP to verify an email for account creation (no existing account required)."""
        def post(self):
            body = request.get_json() or {}
            email = body.get('email', '').strip().lower()

            if not email:
                return {'message': 'Email is required'}, 400

            otp = str(random.randint(100000, 999999))
            _otp_store[f"signup:{email}"] = {
                'otp': otp,
                'expires': datetime.now() + timedelta(minutes=10)
            }

            smtp_user = os.environ.get('SMTP_USER')
            smtp_pass = os.environ.get('SMTP_PASSWORD')

            if not smtp_user or not smtp_pass:
                print(f"[OTP DEV] Signup code for {email}: {otp}")
                return {'message': 'Dev mode: use the code below (SMTP not configured)', 'dev_otp': otp}, 200

            try:
                msg = MIMEText(
                    f"Your account verification code is: {otp}\n\n"
                    f"This code expires in 10 minutes.\n"
                    f"If you did not request this, ignore this email."
                )
                msg['Subject'] = 'Account Verification Code'
                msg['From'] = smtp_user
                msg['To'] = email
                with smtplib.SMTP('smtp.gmail.com', 587) as s:
                    s.starttls()
                    s.login(smtp_user, smtp_pass)
                    s.sendmail(smtp_user, email, msg.as_string())
            except Exception as e:
                return {'message': f'Failed to send email: {str(e)}'}, 500

            return {'message': 'Verification code sent to your email'}, 200

    class _SignupVerify(Resource):
        """Verify signup OTP — just confirms the code is valid, does not create account."""
        def post(self):
            body = request.get_json() or {}
            email = body.get('email', '').strip().lower()
            otp = str(body.get('otp', '')).strip()

            if not email or not otp:
                return {'message': 'Email and code are required'}, 400

            key = f"signup:{email}"
            stored = _otp_store.get(key)
            if not stored:
                return {'message': 'No pending code for this email. Request a new one.'}, 400

            if datetime.now() > stored['expires']:
                _otp_store.pop(key, None)
                return {'message': 'Code expired. Request a new one.'}, 400

            if stored['otp'] != otp:
                return {'message': 'Invalid code'}, 401

            _otp_store.pop(key, None)
            return {'message': 'Email verified', 'email': email}, 200


api.add_resource(OTPApi._Send, '/otp/send')
api.add_resource(OTPApi._Verify, '/otp/verify')
api.add_resource(OTPApi._SignupSend, '/otp/signup/send')
api.add_resource(OTPApi._SignupVerify, '/otp/signup/verify')
api.add_resource(OTPApi._GoogleLogin, '/google/login')
