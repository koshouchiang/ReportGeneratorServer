from unittest import mock
import json

def mock_access_token():
    """
    Create a access token with a fake user,
    mocked the return value of the access token with User.Id = 1.
    """
    
    report_server_token = "711565b38b1c85510998e256e74b7cc73d558b7cbe77ad52ba0f1b3da276a597"

    return report_server_token


def mock_firebase_id_token(uid: str = 'test_uid'):
    """
    Create a fake firebase_auth object,
    mocked the return value of the 'VerifyToken' method with it.
    """
    # create a fake auth.
    from utility.firebase.model import FirebaseAuth
    fake_firebase_auth = FirebaseAuth(uid=uid,
                                      audience='test_audience',
                                      provider='test_provider',
                                      identity='test_identity',
                                      authentication_time=1610958465)

    # mock Verify result.
    from utility.firebase.globals import firebase_auth
    firebase_auth.VerifyToken = mock.Mock(return_value=fake_firebase_auth)

    return fake_firebase_auth


def mock_token_pair():
    """
    Create a access token with a fake user,
    mocked the return value of the access token with User.Id = 1.
    """
    # create fake token.
    from utility.jwt.func import CreateAccessToken, CreateRefreshToken
    access_payload = dict(UserCode='test_user_code')
    access_token = CreateAccessToken(access_payload)

    refresh_payload = dict(Uid='test_uid')
    refresh_token = CreateRefreshToken(refresh_payload)

    from application import model
    model.CreateAccessToken = mock.Mock(return_value=access_token)
    model.CreateRefreshToken = mock.Mock(return_value=refresh_token)

    ret = {
        'access_token': access_token,
        'refresh_token': refresh_token
    }

    return ret
