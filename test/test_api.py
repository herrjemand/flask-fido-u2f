import unittest, json

from flask import Flask, session
from flask_fido_u2f import U2F

from .soft_u2f_v2 import SoftU2FDevice

class APITest(unittest.TestCase):
    def setUp(self):
        self.app      = Flask(__name__)
        self.client   = self.app.test_client()
        
        self.app.config['SECRET_KEY'] = 'DjInNB3l9GBZq2D9IsbBuHpOiLI5H1iBdqJR24VPHdj'
        self.app.config['U2F_APPID']  = 'https://example.com'

        self.u2f       = U2F(self.app)
        self.u2f_keys  = []

        self.u2f_token = SoftU2FDevice()

        @self.u2f.read
        def read():
            return self.u2f_keys

        @self.u2f.save
        def save(u2fdata):
            self.u2f_keys = u2fdata

        @self.u2f.success
        def success():
            pass

        @self.u2f.fail
        def fail():
            pass

    def test_enroll(self):

    # ----- Checking unauthorized enroll get ----- #
        response = self.client.get('/enroll')

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers['Content-Type'], 'application/json')
        response_json = json.loads(response.get_data(as_text=True))

        self.assertDictEqual(response_json, {
            'status' : 'failed', 
            'error'  : 'Unauthorized!'
        })

    # ----- Checking GET enroll structure ----- #

        with self.client as c:
            with c.session_transaction() as sess:
                sess['u2f_enroll_authorized'] = True

        response = self.client.get('/enroll')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Content-Type'], 'application/json')

        response_json = json.loads(response.get_data(as_text=True))

        enroll_seed_model = {
            'status'               : str,
            'registerRequests'     : list,
            'authenticateRequests' : list
        }

        enroll_seed_model_registerRequests = {
            'appId'     : str,
            'challenge' : str,
            'version'   : str
        }

        self.assertEqual(response_json['status'], 'ok')

        self.assertTrue(all(type(response_json[key]) == enroll_seed_model[key] for key in enroll_seed_model.keys()))

        self.assertTrue(all(type(response_json['registerRequests'][0][key]) == enroll_seed_model_registerRequests[key] for key in enroll_seed_model_registerRequests.keys()))
        
        self.assertEqual(response_json['registerRequests'][0]['version'], 'U2F_V2')

    # ----- Verifying enroll ----- #
    
      # ----- 400 BAD REQUEST ----- #
        challenge = response_json['registerRequests'][0]
        keyhandle = self.u2f_token.register(challenge)

        response = self.client.post('/enroll', data=json.dumps(keyhandle), headers={"content-type": "application/json"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.headers['Content-Type'], 'application/json')

        response_json = json.loads(response.get_data(as_text=True))

        self.assertDictEqual(response_json, {
            'error': 'Invalid key handle!', 
            'status': 'failed'
        })

    # ----- 201 CREATED ----- #

        response = self.client.get('/enroll')
        response_json = json.loads(response.get_data(as_text=True))
        
        challenge = response_json['registerRequests'][0]

        keyhandle = self.u2f_token.register(challenge, facet=self.app.config['U2F_APPID'])

        response = self.client.post('/enroll', data=json.dumps(keyhandle), headers={"content-type": "application/json"})

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.headers['Content-Type'], 'application/json')

        response_json = json.loads(response.get_data(as_text=True))

        self.assertDictEqual(response_json, {
            'status'  : 'ok', 
            'message' : 'Successfully enrolled new U2F device!'
        })




    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()

# app.config['U2F_APPID']          = 'https://localhost:5000'
# app.config['U2F_FACETS_ENABLED'] = False
# app.config['U2F_FACETS_LIST']    = ['https://localhost']