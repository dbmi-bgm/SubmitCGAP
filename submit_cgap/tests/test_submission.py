import contextlib
import os
import pytest
import re

from dcicutils.qa_utils import override_environ, ignored, ControlledTime
from unittest import mock
from .test_utils import shown_output
from .. import submission as submission_module
from ..base import PRODUCTION_SERVER
from ..exceptions import CGAPPermissionError
from ..submission import (
    SERVER_REGEXP, check_institution, check_project, do_any_uploads, do_uploads,
    execute_prearranged_upload, get_section, get_user_record, ingestion_submission_item_url,
    resolve_server, resume_uploads, script_catch_errors, show_section, submit_metadata_bundle,
    upload_file_to_uuid, upload_item_data, PROGRESS_CHECK_INTERVAL
)
from ..utils import FakeResponse


SOME_AUTH = ('my-key-id', 'good-secret')

SOME_BAD_AUTH = ('my-key-id', 'bad-secret')

SOME_BAD_RESULT = {'message': 'Houston, we have a problem.'}

SOME_BUNDLE_FILENAME = '/some-folder/foo.xls'

SOME_BUNDLE_FILENAME_FOLDER = os.path.dirname(SOME_BUNDLE_FILENAME)

SOME_ENV = 'some-env'

SOME_FILENAME = 'some-filename'

SOME_SERVER = 'http://localhost:7777'  # Dependencies force this to be out of alphabetical order

SOME_KEYDICT = {'key': 'key7', 'secret': 'secret7', 'server': SOME_SERVER}

SOME_OTHER_BUNDLE_FOLDER = '/some-other-folder/'

SOME_UPLOAD_URL = 'some-url'

SOME_UPLOAD_CREDENTIALS = {
    'AccessKeyId': 'some-access-key',
    'SecretAccessKey': 'some-secret',
    'SessionToken': 'some-session-token',
    'upload_url': SOME_UPLOAD_URL,
}

SOME_UPLOAD_CREDENTIALS_RESULT = {
    '@graph': [
        {'upload_credentials': SOME_UPLOAD_CREDENTIALS}
    ]
}

SOME_UPLOAD_INFO = [
    {'uuid': '1234', 'filename': 'f1.fastq.gz'},
    {'uuid': '9876', 'filename': 'f2.fastq.gz'}
]

SOME_UPLOAD_INFO_RESULT = {
    'additional_data': {
        'upload_info': SOME_UPLOAD_INFO
    }
}

SOME_USER = "jdoe"

SOME_USER_HOMEDIR = os.path.join('/home', SOME_USER)

SOME_UUID = '123-4444-5678'

SOME_ENVIRON = {
    'USER': SOME_USER
}

SOME_ENVIRON_WITH_CREDS = {
    'USER': SOME_USER,
    'AWS_ACCESS_KEY_ID': 'some-access-key',
    'AWS_SECRET_ACCESS_KEY': 'some-secret',
    'AWS_SECURITY_TOKEN': 'some-session-token',
}


def test_server_regexp():

    schemas = ['http', 'https']
    hosts = ['localhost', 'localhost:5000', 'fourfront-cgapfoo.what-ever.com',
             'cgap.hms.harvard.edu', 'foo.bar.cgap.hms.harvard.edu']
    final_slashes = ['/', '']  # 1 or 0 is good

    for schema in schemas:
        for host in hosts:
            for final_slash in final_slashes:
                url_to_check = schema + "://" + host + final_slash
                print("Trying", url_to_check, "expecting match...")
                assert SERVER_REGEXP.match(url_to_check)

    non_matches = [
        "ftp://localhost:8000",
        "ftp://localhost:80ab",
        "http://localhost.localnet",
        "http://foo.bar",
        "https://foo.bar"
    ]

    for non_match in non_matches:
        print("Trying", non_match, "expecting NO match...")
        assert not SERVER_REGEXP.match(non_match)


def test_resolve_server():

    def mocked_get_beanstalk_real_url(env):
        # We don't HAVE to be mocking this function, but it's slow so this will speed up testing. -kmp 4-Sep-2020
        if env == 'fourfront-cgap':
            return PRODUCTION_SERVER
        elif env in ['fourfront-cgapdev', 'fourfront-cgapwolf', 'fourfront-cgaptest']:
            return 'http://' + env + ".something.elasticbeanstalk.com"
        else:
            raise ValueError("Unexpected beanstalk env: %s" % env)

    with mock.patch.object(submission_module, "get_beanstalk_real_url", mocked_get_beanstalk_real_url):

        with pytest.raises(SyntaxError):
            resolve_server(env='something', server='something_else')

        with override_environ(SUBMIT_CGAP_DEFAULT_ENV=None):

            with mock.patch.object(submission_module, "DEFAULT_ENV", None):

                assert resolve_server(env=None, server=None) == PRODUCTION_SERVER

            with mock.patch.object(submission_module, "DEFAULT_ENV", 'fourfront-cgapdev'):

                cgap_dev_server = resolve_server(env=None, server=None)

                assert re.match("http://fourfront-cgapdev[.].*[.]elasticbeanstalk.com",
                                cgap_dev_server)

        with pytest.raises(SyntaxError):
            resolve_server(env='fourfront-cgapfoo', server=None)

        with pytest.raises(SyntaxError):
            resolve_server(env='cgapfoo', server=None)

        with pytest.raises(ValueError):
            resolve_server(server="http://foo.bar", env=None)

        assert re.match("http://fourfront-cgapdev[.].*[.]elasticbeanstalk.com",
                        resolve_server(env='fourfront-cgapdev', server=None))

        assert re.match("http://fourfront-cgapdev[.].*[.]elasticbeanstalk.com",
                        resolve_server(env='cgapdev', server=None))  # Omitting 'fourfront-' is allowed

        assert re.match("http://fourfront-cgapdev[.].*[.]elasticbeanstalk.com",
                        resolve_server(server=cgap_dev_server, env=None))  # Identity operation


good_institution = '/institutions/hms-dbmi/'
good_project = '/projects/12a92962-8265-4fc0-b2f8-cf14f05db58b/'


def make_user_record(title='J Doe',
                     contact_email='jdoe@cgap.hms.harvard.edu',
                     **kwargs):
    user_record = {
        'title': title,
        'contact_email': contact_email,
    }
    user_record.update(kwargs)

    return user_record


def test_get_user_record():

    good_auth = ('mykey', 'mysecret')

    def make_mocked_get(auth_failure_code=400):
        def mocked_get(url, *, auth):
            ignored(url)
            if auth != good_auth:
                return FakeResponse(status_code=auth_failure_code, json={'Title': 'Not logged in.'})
            return FakeResponse(status_code=200, json={'title': 'J Doe', 'contact_email': 'jdoe@cgap.hms.harvard.edu'})
        return mocked_get

    with mock.patch("requests.get", return_value=FakeResponse(401, content='["not dictionary"]')):
        with pytest.raises(CGAPPermissionError):
            get_user_record(server="http://localhost:12345", auth=None)

    with mock.patch("requests.get", make_mocked_get(auth_failure_code=401)):
        with pytest.raises(CGAPPermissionError):
            get_user_record(server="http://localhost:12345", auth=None)

    with mock.patch("requests.get", make_mocked_get(auth_failure_code=403)):
        with pytest.raises(CGAPPermissionError):
            get_user_record(server="http://localhost:12345", auth=None)

    with mock.patch("requests.get", make_mocked_get()):
        get_user_record(server="http://localhost:12345", auth=good_auth)

    with mock.patch("requests.get", lambda *x, **y: FakeResponse(status_code=400)):
        with pytest.raises(Exception):  # Body is not JSON
            get_user_record(server="http://localhost:12345", auth=good_auth)


def test_check_institution():

    assert check_institution(institution=good_institution, user_record='does-not-matter') == good_institution
    assert check_institution(institution='anything', user_record='does-not-matter') == 'anything'

    try:
        check_institution(institution=None, user_record=make_user_record())
    except Exception as e:
        assert str(e).startswith("Your user profile declares no institution")

    try:
        check_institution(institution=None,
                          user_record=make_user_record(submits_for=[]))
    except Exception as e:
        assert str(e).startswith("Your user profile declares no institution")
    else:
        raise AssertionError("Expected error was not raised.")  # pragma: no cover

    successful_result = check_institution(institution=None,
                                          user_record=make_user_record(submits_for=[
                                              {"@id": "/institutions/bwh"}
                                          ]))

    try:
        check_institution(institution=None,
                          user_record=make_user_record(submits_for=[
                              {"@id": "/institutions/hms-dbmi/"},
                              {"@id": "/institutions/bch/"},
                              {"@id": "/institutions/bwh"}
                          ]
                          ))
    except Exception as e:
        assert str(e).startswith("You must use --institution to specify which institution")
    else:
        raise AssertionError("Expected error was not raised.")  # pragma: no cover - we hope never to see this executed

    print("successful_result=", successful_result)

    assert successful_result == "/institutions/bwh"


def test_check_project():

    assert check_project(project=good_project, user_record='does-not-matter') == good_project
    assert check_project(project='anything', user_record='does-not-matter') == 'anything'

    try:
        check_project(project=None, user_record=make_user_record())
    except Exception as e:
        assert str(e).startswith("Your user profile has no project declared")

    try:
        check_project(project=None,
                      user_record=make_user_record(project={}))
    except Exception as e:
        assert str(e).startswith("Your user profile has no project declared")
    else:
        raise AssertionError("Expected error was not raised.")  # pragma: no cover - we hope never to see this executed

    successful_result = check_project(project=None,
                                      user_record=make_user_record(project={'@id': good_project})
                                      )

    print("successful_result=", successful_result)

    assert successful_result == good_project


def test_get_section():

    assert get_section({}, 'foo') is None
    assert get_section({'alpha': 3, 'beta': 4}, 'foo') is None
    assert get_section({'alpha': 3, 'foo': 5, 'beta': 4}, 'foo') == 5
    assert get_section({'additional_data': {}, 'alpha': 3, 'foo': 5, 'beta': 4}, 'omega') is None
    assert get_section({'additional_data': {'omega': 24}, 'alpha': 3, 'foo': 5, 'beta': 4}, 'epsilon') is None
    assert get_section({'additional_data': {'omega': 24}, 'alpha': 3, 'foo': 5, 'beta': 4}, 'omega') == 24


def test_progress_check_interval():

    assert isinstance(PROGRESS_CHECK_INTERVAL, int) and PROGRESS_CHECK_INTERVAL > 0


def test_ingestion_submission_item_url():

    assert ingestion_submission_item_url(
        server='http://foo.com',
        uuid='123-4567-890'
    ) == 'http://foo.com/ingestion-submissions/123-4567-890?format=json'


def test_show_section_without_caveat():

    nothing_to_show = [
        '----- Foo -----',
        'Nothing to show.'
    ]

    # Lines section available, without caveat.
    with shown_output() as shown:
        show_section(
            res={'foo': ['abc', 'def']},
            section='foo',
            caveat_outcome=None)
        assert shown.lines == [
            '----- Foo -----',
            'abc',
            'def',
        ]

    # Lines section available, without caveat, but no section entry.
    with shown_output() as shown:
        show_section(
            res={},
            section='foo',
            caveat_outcome=None
        )
        assert shown.lines == nothing_to_show

    # Lines section available, without caveat, but empty.
    with shown_output() as shown:
        show_section(
            res={'foo': []},
            section='foo',
            caveat_outcome=None
        )
        assert shown.lines == nothing_to_show

    # Lines section available, without caveat, but null.
    with shown_output() as shown:
        show_section(
            res={'foo': None},
            section='foo',
            caveat_outcome=None
        )
        assert shown.lines == nothing_to_show

    # Dictionary section available, without caveat, and with a dictionary.
    with shown_output() as shown:
        show_section(
            res={'foo': {'alpha': 'beta', 'gamma': 'delta'}},
            section='foo',
            caveat_outcome=None
        )
        assert shown.lines == [
            '----- Foo -----',
            '{\n'
            '  "alpha": "beta",\n'
            '  "gamma": "delta"\n'
            '}'
        ]

    # Dictionary section available, without caveat, and with an empty dictionary.
    with shown_output() as shown:
        show_section(
            res={'foo': {}},
            section='foo',
            caveat_outcome=None
        )
        assert shown.lines == nothing_to_show

    # Random unexpected data, with caveat.
    with shown_output() as shown:
        show_section(
            res={'foo': 17},
            section='foo',
            caveat_outcome=None
        )
        assert shown.lines == [
            '----- Foo -----',
            '17',
        ]


def test_show_section_with_caveat():

    # Some output is shown marked by a caveat, that indicates execution stopped early for some reason
    # and the output is partial.

    caveat = 'some error'

    # Lines section available, with caveat.
    with shown_output() as shown:
        show_section(
            res={'foo': ['abc', 'def']},
            section='foo',
            caveat_outcome=caveat
        )
        assert shown.lines == [
            '----- Foo (prior to %s) -----' % caveat,
            'abc',
            'def',
        ]

    # Lines section available, with caveat.
    with shown_output() as shown:
        show_section(
            res={},
            section='foo',
            caveat_outcome=caveat
        )
        assert shown.lines == []  # Nothing shown if there is a caveat specified


def test_script_catch_errors():
    try:
        with script_catch_errors():
            pass
    except SystemExit as e:
        assert e.code == 0, "Expected status code 0, but got %s." % e.code
    else:
        raise AssertionError("SystemExit not raised.")  # pragma: no cover - we hope never to see this executed

    with shown_output() as shown:

        try:
            with script_catch_errors():
                raise RuntimeError("Some error")
        except SystemExit as e:
            assert e.code == 1, "Expected status code 1, but got %s." % e.code
        else:
            raise AssertionError("SystemExit not raised.")  # pragma: no cover - we hope never to see this executed

        assert shown.lines == ["RuntimeError: Some error"]


def test_do_any_uploads():

    # With no files, nothing to query about or load
    with mock.patch.object(submission_module, "yes_or_no", return_value=True) as mock_yes_or_no:
        with mock.patch.object(submission_module, "do_uploads") as mock_uploads:
            do_any_uploads(
                res={'additional_info': {'upload_info': []}},
                keydict={'key': 'key7', 'secret': 'secret7', 'server': 'http://localhost:7777'},
                bundle_filename='/some-folder/foo.xls'
            )
            assert mock_yes_or_no.call_count == 0
            assert mock_uploads.call_count == 0

    with mock.patch.object(submission_module, "yes_or_no", return_value=False) as mock_yes_or_no:
        with mock.patch.object(submission_module, "do_uploads") as mock_uploads:
            with shown_output() as shown:
                do_any_uploads(
                    res={'additional_data': {'upload_info': [{'uuid': '1234', 'filename': 'f1.fastq.gz'}]}},
                    keydict={'key': 'key7', 'secret': 'secret7', 'server': 'http://localhost:7777'},
                    bundle_filename='/some-folder/foo.xls'
                )
                mock_yes_or_no.assert_called_with("Upload 1 file?")
                assert mock_uploads.call_count == 0
                assert shown.lines == ['No uploads attempted.']

    with mock.patch.object(submission_module, "yes_or_no", return_value=True) as mock_yes_or_no:
        with mock.patch.object(submission_module, "do_uploads") as mock_uploads:

            n_uploads = len(SOME_UPLOAD_INFO)

            with shown_output() as shown:
                do_any_uploads(
                    res=SOME_UPLOAD_INFO_RESULT,
                    keydict=SOME_KEYDICT,
                    bundle_filename=SOME_BUNDLE_FILENAME,  # from which a folder can be inferred
                )
                mock_yes_or_no.assert_called_with("Upload %s files?" % n_uploads)
                mock_uploads.assert_called_with(
                    SOME_UPLOAD_INFO,
                    auth=SOME_KEYDICT,
                    folder=SOME_BUNDLE_FILENAME_FOLDER,  # the folder part of given SOME_BUNDLE_FILENAME
                )
                assert shown.lines == []

            with shown_output() as shown:
                do_any_uploads(
                    res=SOME_UPLOAD_INFO_RESULT,
                    keydict=SOME_KEYDICT,
                    bundle_folder=SOME_OTHER_BUNDLE_FOLDER,  # rather than bundle_filename
                )
                mock_yes_or_no.assert_called_with("Upload %s files?" % n_uploads)
                mock_uploads.assert_called_with(
                    SOME_UPLOAD_INFO,
                    auth=SOME_KEYDICT,
                    folder=SOME_OTHER_BUNDLE_FOLDER,  # passed straight through
                )
                assert shown.lines == []

            with shown_output() as shown:
                do_any_uploads(
                    res=SOME_UPLOAD_INFO_RESULT,
                    keydict=SOME_KEYDICT,
                    # No bundle_filename or bundle_folder
                )
                mock_yes_or_no.assert_called_with("Upload %s files?" % n_uploads)
                mock_uploads.assert_called_with(
                    SOME_UPLOAD_INFO,
                    auth=SOME_KEYDICT,
                    folder=None,  # No folder
                )
                assert shown.lines == []


def test_resume_uploads():

    @contextlib.contextmanager
    def script_dont_catch_errors():
        yield

    with mock.patch.object(submission_module, "script_catch_errors", script_dont_catch_errors):
        with mock.patch.object(submission_module, "resolve_server", return_value=SOME_SERVER):
            with mock.patch.object(submission_module, "get_keydict_for_server", return_value=SOME_KEYDICT):
                some_response_json = {'some': 'json'}
                with mock.patch("requests.get", return_value=FakeResponse(200, json=some_response_json)):
                    with mock.patch.object(submission_module, "do_any_uploads") as mock_do_any_uploads:
                        resume_uploads(SOME_UUID, server=SOME_SERVER, env=None, bundle_filename=SOME_BUNDLE_FILENAME,
                                       keydict=SOME_KEYDICT)
                        mock_do_any_uploads.assert_called_with(
                            some_response_json,
                            keydict=SOME_KEYDICT,
                            bundle_filename=SOME_BUNDLE_FILENAME
                        )

    with mock.patch.object(submission_module, "script_catch_errors", script_dont_catch_errors):
        with mock.patch.object(submission_module, "resolve_server", return_value=SOME_SERVER):
            with mock.patch.object(submission_module, "get_keydict_for_server", return_value=SOME_KEYDICT):
                with mock.patch("requests.get", return_value=FakeResponse(401, json=SOME_BAD_RESULT)):
                    with mock.patch.object(submission_module, "do_any_uploads") as mock_do_any_uploads:
                        with pytest.raises(Exception):
                            resume_uploads(SOME_UUID, server=SOME_SERVER, env=None,
                                           bundle_filename=SOME_BUNDLE_FILENAME, keydict=SOME_KEYDICT)
                        assert mock_do_any_uploads.call_count == 0


class MockTime:
    def __init__(self, **kwargs):
        self._time = ControlledTime(**kwargs)

    def time(self):
        return (self._time.now() - self._time.INITIAL_TIME).total_seconds()


def test_execute_prearranged_upload():

    with mock.patch.object(os, "environ", SOME_ENVIRON.copy()):
        with shown_output() as shown:
            with pytest.raises(ValueError):
                bad_credentials = SOME_UPLOAD_CREDENTIALS.copy()
                bad_credentials.pop('SessionToken')
                # This will abort quite early because it can't construct a proper set of credentials as env vars.
                # Nothing has to be mocked because it won't get that far.
                execute_prearranged_upload('this-file-name-is-not-used', bad_credentials)
            assert shown.lines == []

    with mock.patch.object(os, "environ", SOME_ENVIRON.copy()):
        with shown_output() as shown:
            with mock.patch("time.time", MockTime().time):
                with mock.patch("subprocess.call", return_value=0) as mock_aws_call:
                    execute_prearranged_upload(path=SOME_FILENAME, upload_credentials=SOME_UPLOAD_CREDENTIALS)
                    mock_aws_call.assert_called_with(
                        ['aws', 's3', 'cp', '--only-show-errors', SOME_FILENAME, SOME_UPLOAD_URL],
                        env=SOME_ENVIRON_WITH_CREDS
                    )
                    assert shown.lines == [
                        "Going to upload some-filename to some-url.",
                        "Uploaded in 1.00 seconds"  # 1 tick (at rate of 1 second per tick in our controlled time)
                    ]

    with mock.patch.object(os, "environ", SOME_ENVIRON.copy()):
        with shown_output() as shown:
            with mock.patch("time.time", MockTime().time):
                with mock.patch("subprocess.call", return_value=17) as mock_aws_call:
                    execute_prearranged_upload(path=SOME_FILENAME, upload_credentials=SOME_UPLOAD_CREDENTIALS)
                    mock_aws_call.assert_called_with(
                        ['aws', 's3', 'cp', '--only-show-errors', SOME_FILENAME, SOME_UPLOAD_URL],
                        env=SOME_ENVIRON_WITH_CREDS
                    )
                    assert shown.lines == [
                        "Going to upload some-filename to some-url.",
                        "Upload failed with exit code 17"
                    ]


def test_upload_file_to_uuid():

    with mock.patch("dcicutils.ff_utils.patch_metadata", return_value=SOME_UPLOAD_CREDENTIALS_RESULT):
        with mock.patch.object(submission_module, "execute_prearranged_upload") as mocked_upload:
            upload_file_to_uuid(filename=SOME_FILENAME, uuid=SOME_UUID, auth=SOME_AUTH)
            mocked_upload.assert_called_with(SOME_FILENAME, upload_credentials=SOME_UPLOAD_CREDENTIALS)

    with mock.patch("dcicutils.ff_utils.patch_metadata", return_value=SOME_BAD_RESULT):
        with mock.patch.object(submission_module, "execute_prearranged_upload") as mocked_upload:
            try:
                upload_file_to_uuid(filename=SOME_FILENAME, uuid=SOME_UUID, auth=SOME_AUTH)
            except Exception as e:
                assert str(e).startswith("Unable to obtain upload credentials")
            else:
                raise Exception("Expected error was not raised.")  # pragma: no cover - we hope this never happens
            assert mocked_upload.call_count == 0


def make_alternator(*values):

    class Alternatives:

        def __init__(self, values):
            self.values = values
            self.pos = 0

        def next_value(self, *args, **kwargs):
            ignored(args, kwargs)
            result = self.values[self.pos]
            self.pos = (self.pos + 1) % len(self.values)
            return result

    alternatives = Alternatives(values)

    return alternatives.next_value


def test_do_uploads():

    @contextlib.contextmanager
    def mock_uploads():

        uploaded = {}

        def mocked_upload_file(filename, uuid, auth):
            if auth != SOME_AUTH:
                raise Exception("Bad auth")
            uploaded[uuid] = filename

        with mock.patch.object(submission_module, "upload_file_to_uuid", mocked_upload_file):
            yield uploaded  # This starts out empty when yielded, but as uploads occur will get populated.

    with mock.patch.object(submission_module, "yes_or_no", return_value=True):

        with mock_uploads() as mock_uploaded:
            do_uploads(upload_spec_list=[], auth=SOME_AUTH)
            assert mock_uploaded == {}

        some_uploads_to_do = [
            {'uuid': '1234', 'filename': 'foo.fastq.gz'},
            {'uuid': '2345', 'filename': 'bar.fastq.gz'},
            {'uuid': '3456', 'filename': 'baz.fastq.gz'}
        ]

        with mock_uploads() as mock_uploaded:
            with shown_output() as shown:
                do_uploads(upload_spec_list=some_uploads_to_do, auth=SOME_BAD_AUTH)
                assert mock_uploaded == {}  # Nothing uploaded because of bad auth
                assert shown.lines == [
                    'Uploading ./foo.fastq.gz to item 1234 ...',
                    'Exception: Bad auth',
                    'Uploading ./bar.fastq.gz to item 2345 ...',
                    'Exception: Bad auth',
                    'Uploading ./baz.fastq.gz to item 3456 ...',
                    'Exception: Bad auth'
                ]

        with mock_uploads() as mock_uploaded:
            with shown_output() as shown:
                do_uploads(upload_spec_list=some_uploads_to_do, auth=SOME_AUTH)
                assert mock_uploaded == {
                    '1234': './foo.fastq.gz',
                    '2345': './bar.fastq.gz',
                    '3456': './baz.fastq.gz'
                }
                assert shown.lines == [
                    'Uploading ./foo.fastq.gz to item 1234 ...',
                    'Upload of ./foo.fastq.gz to item 1234 was successful.',
                    'Uploading ./bar.fastq.gz to item 2345 ...',
                    'Upload of ./bar.fastq.gz to item 2345 was successful.',
                    'Uploading ./baz.fastq.gz to item 3456 ...',
                    'Upload of ./baz.fastq.gz to item 3456 was successful.',
                ]

    with mock.patch.object(submission_module, "yes_or_no", make_alternator(True, False)):

        with mock_uploads() as mock_uploaded:
            with shown_output() as shown:
                do_uploads(
                    upload_spec_list=[
                        {'uuid': '1234', 'filename': 'foo.fastq.gz'},
                        {'uuid': '2345', 'filename': 'bar.fastq.gz'},
                        {'uuid': '3456', 'filename': 'baz.fastq.gz'}
                    ],
                    auth=SOME_AUTH,
                    folder='/x/yy/zzz/'
                )
                assert mock_uploaded == {
                    '1234': '/x/yy/zzz/foo.fastq.gz',
                    # The mock yes_or_no will have omitted this element.
                    # '2345': './bar.fastq.gz',
                    '3456': '/x/yy/zzz/baz.fastq.gz'
                }
                assert shown.lines == [
                    'Uploading /x/yy/zzz/foo.fastq.gz to item 1234 ...',
                    'Upload of /x/yy/zzz/foo.fastq.gz to item 1234 was successful.',
                    # The query about uploading bar.fastq has been mocked out here
                    # in favor of an unconditional False result, so the question does no I/O.
                    # The only output is the result of simulating a 'no' answer.
                    'OK, not uploading it.',
                    'Uploading /x/yy/zzz/baz.fastq.gz to item 3456 ...',
                    'Upload of /x/yy/zzz/baz.fastq.gz to item 3456 was successful.',
                ]


def test_upload_item_data():

    with mock.patch.object(submission_module, "resolve_server", return_value=SOME_SERVER) as mock_resolve:
        with mock.patch.object(submission_module, "get_keydict_for_server", return_value=SOME_KEYDICT) as mock_get:
            with mock.patch.object(submission_module, "yes_or_no", return_value=True):
                with mock.patch.object(submission_module, "upload_file_to_uuid") as mock_upload:

                    upload_item_data(part_filename=SOME_FILENAME, uuid=SOME_UUID, server=SOME_SERVER, env=SOME_ENV)

                    mock_resolve.assert_called_with(env=SOME_ENV, server=SOME_SERVER)
                    mock_get.assert_called_with(SOME_SERVER)
                    mock_upload.assert_called_with(filename=SOME_FILENAME, uuid=SOME_UUID, auth=SOME_KEYDICT)

    with mock.patch.object(submission_module, "resolve_server", return_value=SOME_SERVER) as mock_resolve:
        with mock.patch.object(submission_module, "get_keydict_for_server", return_value=SOME_KEYDICT) as mock_get:
            with mock.patch.object(submission_module, "yes_or_no", return_value=False):
                with mock.patch.object(submission_module, "upload_file_to_uuid") as mock_upload:

                    with shown_output() as shown:

                        try:
                            upload_item_data(part_filename=SOME_FILENAME, uuid=SOME_UUID, server=SOME_SERVER,
                                             env=SOME_ENV)
                        except SystemExit as e:
                            assert e.code == 1
                        else:
                            raise AssertionError("Expected SystemExit not raised.")  # pragma: no cover

                        assert shown.lines == ['Aborting submission.']

                    mock_resolve.assert_called_with(env=SOME_ENV, server=SOME_SERVER)
                    mock_get.assert_called_with(SOME_SERVER)
                    assert mock_upload.call_count == 0


def test_submit_metadata_bundle():
    # TODO: Write this test.
    ignored(submit_metadata_bundle)


# def submit_metadata_bundle(bundle_filename, institution, project, server, env, validate_only):
#
#     with script_catch_errors():
#
#         server = resolve_server(server=server, env=env)
#
#         validation_qualifier = " (for validation only)" if validate_only else ""
#
#         if not yes_or_no("Submit %s to %s%s?" % (bundle_filename, server, validation_qualifier)):
#             show("Aborting submission.")
#             exit(1)
#
#         keydict = get_keydict_for_server(server)
#         keypair = keydict_to_keypair(keydict)
#
#         user_record = get_user_record(server, auth=keypair)
#
#         institution = check_institution(institution, user_record)
#         project = check_project(project, user_record)
#
#         if not os.path.exists(bundle_filename):
#             raise ValueError("The file '%s' does not exist." % bundle_filename)
#
#         post_files = {
#             "datafile": io.open(bundle_filename, 'rb')
#         }
#
#         post_data = {
#             'ingestion_type': 'metadata_bundle',
#             'institution': institution,
#             'project': project,
#             'validate_only': validate_only,
#         }
#
#         submission_url = server + "/submit_for_ingestion"
#
#         res = requests.post(submission_url, auth=keypair, data=post_data, files=post_files).json()
#
#         # print(json.dumps(res, indent=2))
#
#         uuid = res['submission_id']
#
#         show("Bundle uploaded, assigned uuid %s for tracking. Awaiting processing..." % uuid, with_time=True)
#
#         tracking_url = ingestion_submission_item_url(server=server, uuid=uuid)
#
#         outcome = None
#         n_tries = 8
#         tries_left = n_tries
#         done = False
#         while tries_left > 0:
#             # Pointless to hit the queue immediately, so we avoid some
#             # server stress by sleeping even before the first try.
#             time.sleep(PROGRESS_CHECK_INTERVAL)
#             res = requests.get(tracking_url, auth=keypair).json()
#             processing_status = res['processing_status']
#             done = processing_status['state'] == 'done'
#             if done:
#                 outcome = processing_status['outcome']
#                 break
#             else:
#                 progress = processing_status['progress']
#                 show("Progress is %s. Continuing to wait..." % progress, with_time=True)
#             tries_left -= 1
#
#         if not done:
#             show("Timed out after %d tries." % n_tries, with_time=True)
#             exit(1)
#
#         show("Final status: %s" % outcome, with_time=True)
#
#         if outcome == 'error' and res.get('errors'):
#             show_section(res, 'errors')
#
#         caveat_outcome = None if outcome == 'success' else outcome
#
#         show_section(res, 'validation_output', caveat_outcome=caveat_outcome)
#
#         if validate_only:
#             exit(0)
#
#         show_section(res, 'post_output', caveat_outcome=caveat_outcome)
#
#         if outcome == 'success':
#             show_section(res, 'upload_info')
#             do_any_uploads(res, keydict, bundle_filename=bundle_filename)
