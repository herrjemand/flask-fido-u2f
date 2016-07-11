import json, time

# Flask imports
from flask import jsonify, session
from flask import Response, request

# U2F imports
from u2flib_server.jsapi import DeviceRegistration
from u2flib_server.u2f import (start_register, complete_register, start_authenticate, verify_authenticate)


class U2F():
    def __init__(self, app, *args
        , enroll_route  = '/u2f/enroll'
        , sign_route    = '/u2f/sign'
        , devices_route = '/u2f/devices'
        , facets_route  = '/u2f/facets.json'):

        self.app              = app

        self.enroll_route     = enroll_route
        self.sign_route       = sign_route
        self.devices_route    = devices_route
        self.facets_route     = facets_route

        self.get_u2f_devices  = None
        self.save_u2f_devices = None

        self.call_success_enroll = None
        self.call_fail_enroll    = None
        self.call_success_sign   = None
        self.call_fail_sign      = None
        self.call_success        = None
        self.call_fail           = None

        # U2F Variables
        self.APPID           = None
        self.FACETS_ENABLED  = False
        self.FACETS_LIST     = None

        self.integrity_check = False 

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.add_url_rule(self.enroll_route,  view_func = self.enroll,  methods=['GET', 'POST'])
        app.add_url_rule(self.sign_route,    view_func = self.sign,    methods=['GET', 'POST'])
        app.add_url_rule(self.devices_route, view_func = self.devices, methods=['GET', 'DELETE'])
        app.add_url_rule(self.facets_route,  view_func = self.facets,  methods=['GET'])

        self.APPID            = self.app.config.get('U2F_APPID', None)
        self.FACETS_ENABLED   = self.app.config.get('U2F_FACETS_ENABLED', False)
        self.FACETS_LIST      = self.app.config.get('U2F_FACETS_LIST', [])

        # Set appid to appid + /facets.json if U2F_FACETS_ENABLED
        # or U2F_APP becomes U2F_FACETS_LIST
        if self.FACETS_ENABLED:
            self.APPID += '/facets.json'
        else:
            self.FACETS_LIST = [self.APPID]


    def verify_integrity(self):
        """Verifies that all required functions been injected."""
        if not self.integrity_check:
            if not self.APPID:
                raise Exception('U2F_APPID was not defined! Please define it in configuration file.')

            if self.FACETS_ENABLED and not len(self.FACETS_LIST):
                raise Exception("""U2F facets been enabled, but U2F facet list is empty.
                                   Please either disable facets by setting U2F_FACETS_ENABLED to False.
                                   Or add facets list using, by assigning it to U2F_FACETS_LIST.
                                """)

            # Injection
            if not self.get_u2f_devices:
                raise Exception('Read is not defined! Please import read through @u2f.read!')

            if not self.save_u2f_devices:
                raise Exception('Save is not defined! Please import read through @u2f.save!')


            if not self.call_success_enroll:
                raise Exception('U2F {name} handler is not defined! Please import {name} through {method}!'.format(name='enroll onSuccess', method='@u2f.enroll_on_success'))

            if not self.call_fail_enroll:
                raise Exception('U2F {name} handler is not defined! Please import {name} through {method}!'.format(name='sign onFail', method='@u2f.enroll_on_fail'))

            if not self.call_success_sign:
                raise Exception('U2F {name} handler is not defined! Please import {name} through {method}!'.format(name='sign onSuccess', method='@u2f.sign_on_success'))

            if not self.call_fail_sign:
                raise Exception('U2F {name} handler is not defined! Please import {name} through {method}!'.format(name='sign onFail', method='@u2f.sign_on_fail'))

            self.integrity_check = True

        return True

# ---- ----- #
    def enroll(self):
        """Enrollment function"""
        self.verify_integrity()

        if session.get('u2f_enroll_authorized', False):
            if request.method == 'GET':
                return jsonify(self.get_enroll()), 200

            elif request.method == 'POST':
                response = self.verify_enroll(request.json)

                if response['status'] == 'ok':
                    return jsonify(response), 201
                else:
                    return jsonify(response), 400

        return jsonify({'status': 'failed', 'error': 'Unauthorized!'}), 401

    def sign(self):
        """Signature function"""
        self.verify_integrity()
        
        if session.get('u2f_sign_required', False):
            if request.method == 'GET':
                response = self.get_signature_challenge()

                if response['status'] == 'ok':
                    return jsonify(response), 200
                else:
                    return jsonify(response), 404

            elif request.method == 'POST':
                response = self.verify_signature(request.json)

                if response['status'] == 'ok':
                    return jsonify(response), 201
                else:
                    return jsonify(response), 400

        return jsonify({'status': 'failed', 'error': 'Unauthorized!'}), 401


    def devices(self):
        """Manages users enrolled u2f devices"""
        self.verify_integrity()

        if session.get('u2f_allow_device_management', False):
            if request.method == 'GET':
                return jsonify(self.get_devices()), 200
            elif request.method == 'DELETE':
                response = self.remove_device(request.json)

                if response['status'] == 'ok':
                    return jsonify(response), 200
                else:
                    return jsonify(response), 404

        return jsonify({'status': 'failed', 'error': 'Unauthorized!'}), 401

    def facets(self):
        """Provides facets support. REQUIRES VALID HTTPS!"""
        self.verify_integrity()

        if self.FACETS_ENABLED:
            data = json.dumps({
                'trustedFacets' : [{
                    'version': { 'major': 1, 'minor' : 0 },
                    'ids': self.FACETS_LIST
                }]
            }, sort_keys=True, indent=2, separators=(',', ': '))

            mime = 'application/fido.trusted-apps+json'
            resp = Response(data, mimetype=mime)

            return resp, 200
        else:
            return jsonify({}), 404

# ----- Methods -----#

    def get_enroll(self):
        """Returns new enroll seed"""

        devices = [DeviceRegistration.wrap(device) for device in self.get_u2f_devices()]
        enroll  = start_register(self.APPID, devices)
        enroll['status'] = 'ok'

        session['_u2f_enroll_'] = enroll.json
        return enroll

    def verify_enroll(self, response):
        """Verifies and saves U2F enroll"""

        seed = session.pop('_u2f_enroll_')
        try:
            new_device, cert = complete_register(seed, response, self.FACETS_LIST)
        except Exception as e:
            self.call_fail_enroll()

            return {
                'status' : 'failed', 
                'error'  : 'Invalid key handle!'
            }

        finally:
            pass
        
        # Setting new device counter to 0
        new_device['counter']   = 0
        new_device['timestamp'] = int(time.time())

        devices = self.get_u2f_devices()
        devices.append(new_device)
        self.save_u2f_devices(devices)
        
        self.call_success_enroll()

        return {'status': 'ok', 'message': 'Successfully enrolled new U2F device!'}


    def get_signature_challenge(self):
        """Returns new signature challenge"""

        devices = [DeviceRegistration.wrap(device) for device in self.get_u2f_devices()]

        if devices == []:
            return {
                'status' : 'failed', 
                'error'  : 'No devices been associated with the account!'
            }

        challenge = start_authenticate(devices)
        challenge['status'] = 'ok'

        session['_u2f_challenge_'] = challenge.json

        return challenge

    def verify_signature(self, signature):
        """Verifies signature"""

        devices   = [DeviceRegistration.wrap(device) for device in self.get_u2f_devices()]
        challenge = session.pop('_u2f_challenge_')

        try:
            counter, touch = verify_authenticate(devices, challenge, signature, self.FACETS_LIST)
        except Exception as e:
            return {
                'status':'failed', 
                'error': 'Invalid Signature!'
            }

            self.call_fail_sign()

        if self.verify_counter(signature, counter):
            session['logged_in'] = True
            return {
                'status'  : 'ok',
                'counter' : counter
            }

            self.call_success_sign()

        else:
            return {
                'status':'failed', 
                'error': 'Device clone detected!'
            }

            self.call_fail_sign()

    def get_devices(self):
        """Returns list of enrolled U2F devices"""

        return {
            'status'  : 'ok',
            'devices' : [
                {
                    'id'        : device['keyHandle'],
                    'timestamp' : device['timestamp']
                } for device in self.get_u2f_devices()
            ]
        }

    def remove_device(self, request):
        """Removes device specified by id"""
        
        devices = self.get_u2f_devices()

        for i in range(len(devices)):
            if devices[i]['keyHandle'] == request.id:
                del devices[i]
                self.save_u2f_devices(devices)

                return {
                    'status'  : 'ok', 
                    'message' : 'Successfully deleted your device!'
                }

        return {
            'status' : 'failed', 
            'error'  : 'No device with such an id been found!'
        }


# ----- Utilities ----- #
    def verify_certificate(self, signature):
        """FUTURE: if enforced policy, verify certificate in public directory"""
        pass

    def verify_counter(self, signature, counter):
        """ Verifies that counter value is greater than previous signature""" 

        devices = self.get_u2f_devices()

        for device in devices:
            # Searching for specific keyhandle
            if device['keyHandle'] == signature['keyHandle']:
                if counter > device['counter']:
                    
                    # Updating counter record
                    device['counter'] = counter
                    self.save_u2f_devices(devices)
                    
                    return True
                else:
                    return False


# ----- Injectors ----- #
    def read(self, func):
        """Injects read function that reads and returns U2F object"""
        self.get_u2f_devices = func

    def save(self, func):
        """Injects save function that takes U2F object and saves it"""
        self.save_u2f_devices = func

    def enroll_on_success(self, func):
        """Injects function that would be called on successfull enrollment"""
        self.call_success_enroll = func

    def enroll_on_fail(self, func):
        """Injects function that would be called on enrollment failure"""
        self.call_fail_enroll = func

    def sign_on_success(self, func):
        """Injects function that would be called on successfull U2F authentication"""
        self.call_success_sign = func

    def sign_on_fail(self, func):
        """Injects function that would be called on U2F authentication failure"""
        self.call_fail_sign = func
